/// File type detection for optimal compression strategy
/// Detects file types before CES pipeline to apply appropriate compression
use std::path::Path;

/// Detected file type
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FileType {
    /// Already compressed (zip, gz, 7z, etc.)
    Compressed,
    /// Image formats (jpg, png, gif, etc.)
    Image,
    /// Video formats (mp4, avi, mkv, etc.)
    Video,
    /// Audio formats (mp3, flac, wav, etc.)
    Audio,
    /// Text files (txt, log, json, xml, etc.)
    Text,
    /// Binary executables and libraries
    Binary,
    /// Unknown type
    Unknown,
}

impl FileType {
    /// Get recommended compression level for this file type
    /// Returns: compression level (0-9 for zstd, 0=no compression)
    pub fn recommended_compression_level(&self) -> i32 {
        match self {
            FileType::Compressed => 0, // Don't recompress
            FileType::Image => 1,      // Light compression (often already compressed)
            FileType::Video => 0,      // Don't compress (already compressed)
            FileType::Audio => 1,      // Light compression (depends on format)
            FileType::Text => 9,       // Maximum compression (very effective)
            FileType::Binary => 6,     // Moderate compression
            FileType::Unknown => 3,    // Default safe level
        }
    }

    /// Check if this file type should skip compression entirely
    pub fn skip_compression(&self) -> bool {
        matches!(self, FileType::Compressed | FileType::Video)
    }

    /// Get display name for this file type
    pub fn name(&self) -> &'static str {
        match self {
            FileType::Compressed => "Compressed Archive",
            FileType::Image => "Image",
            FileType::Video => "Video",
            FileType::Audio => "Audio",
            FileType::Text => "Text",
            FileType::Binary => "Binary",
            FileType::Unknown => "Unknown",
        }
    }
}

/// File type detector
pub struct FileDetector;

impl FileDetector {
    /// Detect file type from path extension
    pub fn detect_from_path(path: &Path) -> FileType {
        if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
            Self::detect_from_extension(ext)
        } else {
            FileType::Unknown
        }
    }

    /// Detect file type from extension string
    pub fn detect_from_extension(ext: &str) -> FileType {
        let ext_lower = ext.to_lowercase();

        // Compressed archives
        if matches!(
            ext_lower.as_str(),
            "zip" | "gz" | "bz2" | "xz" | "7z" | "tar" | "rar" | "zst" | "lz4"
        ) {
            return FileType::Compressed;
        }

        // Images
        if matches!(
            ext_lower.as_str(),
            "jpg" | "jpeg" | "png" | "gif" | "bmp" | "tiff" | "webp" | "svg" | "ico"
        ) {
            return FileType::Image;
        }

        // Video
        if matches!(
            ext_lower.as_str(),
            "mp4" | "avi" | "mkv" | "mov" | "wmv" | "flv" | "webm" | "m4v" | "mpg" | "mpeg"
        ) {
            return FileType::Video;
        }

        // Audio
        if matches!(
            ext_lower.as_str(),
            "mp3" | "wav" | "flac" | "aac" | "ogg" | "wma" | "m4a" | "opus"
        ) {
            return FileType::Audio;
        }

        // Text
        if matches!(
            ext_lower.as_str(),
            "txt"
                | "log"
                | "json"
                | "xml"
                | "yaml"
                | "yml"
                | "toml"
                | "ini"
                | "md"
                | "rst"
                | "csv"
                | "tsv"
                | "html"
                | "htm"
                | "css"
                | "js"
                | "py"
                | "rs"
                | "go"
                | "c"
                | "cpp"
                | "h"
                | "java"
                | "sh"
                | "bash"
        ) {
            return FileType::Text;
        }

        // Binary
        if matches!(
            ext_lower.as_str(),
            "exe" | "dll" | "so" | "dylib" | "o" | "a" | "lib" | "bin" | "dat"
        ) {
            return FileType::Binary;
        }

        FileType::Unknown
    }

    /// Detect file type from magic bytes (file signature)
    pub fn detect_from_content(data: &[u8]) -> FileType {
        if data.len() < 4 {
            return FileType::Unknown;
        }

        // Check common magic bytes
        match &data[0..4] {
            // ZIP: 50 4B 03 04
            [0x50, 0x4B, 0x03, 0x04] => FileType::Compressed,
            // GZIP: 1F 8B
            [0x1F, 0x8B, ..] => FileType::Compressed,
            // PNG: 89 50 4E 47
            [0x89, 0x50, 0x4E, 0x47] => FileType::Image,
            // JPEG: FF D8 FF
            [0xFF, 0xD8, 0xFF, _] => FileType::Image,
            // GIF: 47 49 46 38
            [0x47, 0x49, 0x46, 0x38] => FileType::Image,
            // MP4/M4V: various, check 'ftyp'
            _ if data.len() >= 12 && &data[4..8] == b"ftyp" => FileType::Video,
            // AVI: 52 49 46 46 ... 41 56 49 20
            [0x52, 0x49, 0x46, 0x46] if data.len() >= 12 && &data[8..12] == b"AVI " => {
                FileType::Video
            }
            // MP3: FF Fx where x is in range (MPEG audio frame sync)
            // Common values: FF FB (layer 3), FF F3 (layer 3), FF F2 (layer 3)
            [0xFF, b, ..] if *b >= 0xF0 && (*b & 0xE0) == 0xE0 => FileType::Audio,
            // FLAC: 66 4C 61 43
            [0x66, 0x4C, 0x61, 0x43] => FileType::Audio,
            // WAV: 52 49 46 46 ... 57 41 56 45
            [0x52, 0x49, 0x46, 0x46] if data.len() >= 12 && &data[8..12] == b"WAVE" => {
                FileType::Audio
            }
            // ELF executable: 7F 45 4C 46
            [0x7F, 0x45, 0x4C, 0x46] => FileType::Binary,
            // Windows PE: 4D 5A
            [0x4D, 0x5A, ..] => FileType::Binary,
            // Check if looks like text (all printable ASCII)
            _ => {
                if Self::is_likely_text(data) {
                    FileType::Text
                } else {
                    FileType::Unknown
                }
            }
        }
    }

    /// Check if data looks like text (heuristic)
    fn is_likely_text(data: &[u8]) -> bool {
        let sample_size = data.len().min(512);
        let sample = &data[0..sample_size];

        let mut printable_count = 0;
        for &byte in sample {
            if byte.is_ascii_graphic() || byte.is_ascii_whitespace() {
                printable_count += 1;
            }
        }

        // If more than 90% is printable ASCII, likely text
        printable_count as f64 / sample_size as f64 > 0.9
    }

    /// Comprehensive detection using both path and content
    pub fn detect(path: &Path, data: &[u8]) -> FileType {
        // First try extension
        let from_path = Self::detect_from_path(path);
        if from_path != FileType::Unknown {
            // Verify with content if possible
            let from_content = Self::detect_from_content(data);
            if from_content != FileType::Unknown && from_content != from_path {
                // If content detection disagrees, trust content over extension
                return from_content;
            }
            return from_path;
        }

        // Fall back to content detection
        Self::detect_from_content(data)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extension_detection() {
        assert_eq!(
            FileDetector::detect_from_extension("zip"),
            FileType::Compressed
        );
        assert_eq!(FileDetector::detect_from_extension("jpg"), FileType::Image);
        assert_eq!(FileDetector::detect_from_extension("mp4"), FileType::Video);
        assert_eq!(FileDetector::detect_from_extension("mp3"), FileType::Audio);
        assert_eq!(FileDetector::detect_from_extension("txt"), FileType::Text);
        assert_eq!(FileDetector::detect_from_extension("exe"), FileType::Binary);
    }

    #[test]
    fn test_magic_bytes() {
        // ZIP
        let zip_data = vec![0x50, 0x4B, 0x03, 0x04, 0x00, 0x00];
        assert_eq!(
            FileDetector::detect_from_content(&zip_data),
            FileType::Compressed
        );

        // PNG
        let png_data = vec![0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A];
        assert_eq!(
            FileDetector::detect_from_content(&png_data),
            FileType::Image
        );

        // Text (all printable ASCII)
        let text_data = b"Hello, World! This is a text file.";
        assert_eq!(FileDetector::detect_from_content(text_data), FileType::Text);
    }

    #[test]
    fn test_compression_levels() {
        assert_eq!(FileType::Compressed.recommended_compression_level(), 0);
        assert_eq!(FileType::Text.recommended_compression_level(), 9);
        assert_eq!(FileType::Video.recommended_compression_level(), 0);
        assert!(FileType::Compressed.skip_compression());
        assert!(FileType::Video.skip_compression());
        assert!(!FileType::Text.skip_compression());
    }

    #[test]
    fn test_file_type_names() {
        assert_eq!(FileType::Compressed.name(), "Compressed Archive");
        assert_eq!(FileType::Text.name(), "Text");
    }
}
