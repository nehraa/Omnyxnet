/// Phase 1: Media Codec Support for Low-Latency Streaming
///
/// This module provides integration with Opus audio codec and documentation
/// for VP9/AV1 video codecs as specified in Phase 1 requirements.
///
/// Opus provides:
/// - Low latency (2.5ms to 60ms)
/// - High audio quality
/// - Adaptable bitrate
/// - Loss tolerance for lossy networks
use anyhow::Result;
use opus::{Channels, Application, Encoder as OpusEncoder, Decoder as OpusDecoder};
use tracing::{debug, info};

/// Audio codec configuration for real-time communication
#[derive(Debug, Clone)]
pub struct AudioConfig {
    /// Sample rate in Hz (8000, 12000, 16000, 24000, or 48000)
    pub sample_rate: u32,
    /// Number of audio channels (1 = mono, 2 = stereo)
    pub channels: Channels,
    /// Target bitrate in bits per second (6000 - 510000)
    pub bitrate: i32,
    /// Frame duration in milliseconds (2.5, 5, 10, 20, 40, or 60)
    pub frame_duration_ms: f32,
}

impl Default for AudioConfig {
    fn default() -> Self {
        Self {
            sample_rate: 48000,          // 48kHz for high quality
            channels: Channels::Stereo,   // Stereo
            bitrate: 64000,               // 64 kbps
            frame_duration_ms: 20.0,      // 20ms frames (low latency)
        }
    }
}

impl AudioConfig {
    /// Create low-latency configuration optimized for real-time communication
    pub fn low_latency() -> Self {
        Self {
            sample_rate: 48000,
            channels: Channels::Mono,     // Mono reduces bandwidth
            bitrate: 32000,               // 32 kbps
            frame_duration_ms: 10.0,      // 10ms frames (very low latency)
        }
    }

    /// Create high-quality configuration for music/podcast
    pub fn high_quality() -> Self {
        Self {
            sample_rate: 48000,
            channels: Channels::Stereo,
            bitrate: 128000,              // 128 kbps
            frame_duration_ms: 20.0,
        }
    }

    /// Calculate frame size in samples
    pub fn frame_size(&self) -> usize {
        (self.sample_rate as f32 * self.frame_duration_ms / 1000.0) as usize
    }

    /// Calculate maximum packet size in bytes
    pub fn max_packet_size(&self) -> usize {
        // Opus maximum packet size is 1275 bytes per RFC 6716
        1275
    }
}

/// Opus audio encoder for low-latency streaming
pub struct AudioEncoder {
    encoder: OpusEncoder,
    config: AudioConfig,
}

impl AudioEncoder {
    /// Create a new audio encoder with the given configuration
    pub fn new(config: AudioConfig) -> Result<Self> {
        let mut encoder = OpusEncoder::new(
            config.sample_rate,
            config.channels,
            Application::Voip,  // Optimized for low latency VoIP
        )?;
        
        // Set the configured bitrate
        encoder.set_bitrate(opus::Bitrate::Bits(config.bitrate))?;
        
        info!("Created Opus encoder: {}Hz, {:?}, {}bps, {}ms frames",
              config.sample_rate, config.channels, config.bitrate, config.frame_duration_ms);

        Ok(Self { encoder, config })
    }

    /// Encode PCM audio samples to Opus
    /// 
    /// Input: PCM samples (16-bit signed integers)
    /// Output: Compressed Opus packet
    pub fn encode(&mut self, pcm: &[i16]) -> Result<Vec<u8>> {
        let frame_size = self.config.frame_size();
        let expected_samples = frame_size * self.config.channels as usize;
        
        if pcm.len() != expected_samples {
            anyhow::bail!("Invalid PCM frame size: expected {} samples, got {}",
                         expected_samples, pcm.len());
        }

        let mut output = vec![0u8; self.config.max_packet_size()];
        let len = self.encoder.encode(pcm, &mut output)?;
        output.truncate(len);
        
        debug!("Encoded {} PCM samples to {} bytes", pcm.len(), len);
        Ok(output)
    }

    /// Set the encoder bitrate dynamically
    pub fn set_bitrate(&mut self, bitrate: i32) -> Result<()> {
        self.encoder.set_bitrate(opus::Bitrate::Bits(bitrate))?;
        self.config.bitrate = bitrate;
        Ok(())
    }
}

/// Opus audio decoder for low-latency streaming
pub struct AudioDecoder {
    decoder: OpusDecoder,
    config: AudioConfig,
}

impl AudioDecoder {
    /// Create a new audio decoder with the given configuration
    pub fn new(config: AudioConfig) -> Result<Self> {
        let decoder = OpusDecoder::new(
            config.sample_rate,
            config.channels,
        )?;
        
        info!("Created Opus decoder: {}Hz, {:?}",
              config.sample_rate, config.channels);

        Ok(Self { decoder, config })
    }

    /// Decode Opus packet to PCM audio samples
    /// 
    /// Input: Compressed Opus packet
    /// Output: PCM samples (16-bit signed integers)
    pub fn decode(&mut self, opus_packet: &[u8]) -> Result<Vec<i16>> {
        let frame_size = self.config.frame_size();
        let mut output = vec![0i16; frame_size * self.config.channels as usize];
        
        let len = self.decoder.decode(opus_packet, &mut output, false)?;
        output.truncate(len);
        
        debug!("Decoded {} bytes to {} PCM samples", opus_packet.len(), len);
        Ok(output)
    }

    /// Decode with Packet Loss Concealment (PLC)
    /// 
    /// When a packet is lost, this generates synthetic audio to mask the loss
    pub fn decode_plc(&mut self) -> Result<Vec<i16>> {
        let frame_size = self.config.frame_size();
        let mut output = vec![0i16; frame_size * self.config.channels as usize];
        
        // Decode without a packet (FEC/PLC mode)
        let len = self.decoder.decode(&[], &mut output, true)?;
        output.truncate(len);
        
        debug!("Generated {} PLC samples for lost packet", len);
        Ok(output)
    }
}

/// Video codec information (for future implementation)
/// 
/// Phase 1 specifies VP9/AV1 codecs for video streaming. These are documented
/// here but not implemented to avoid heavy dependencies in the MVP.
/// 
/// VP9:
/// - Open-source, royalty-free
/// - Better compression than H.264
/// - Good hardware support
/// - Crate: rav1e (encoder), dav1d (decoder)
/// 
/// AV1:
/// - Next-generation codec
/// - 30% better compression than VP9
/// - Increasing hardware support
/// - Higher CPU requirements for software encoding
/// - Crate: rav1e (encoder), dav1d (decoder)
/// 
/// To enable video support in the future:
/// 1. Add dependencies: rav1e = "0.7", dav1d = "0.10"
/// 2. Create VideoEncoder and VideoDecoder similar to AudioEncoder
/// 3. Configure for low-latency mode (tune for realtime)
/// 4. Integrate with streaming pipeline
pub struct VideoConfig {
    pub width: u32,
    pub height: u32,
    pub framerate: u32,
    pub bitrate: u32,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audio_config_defaults() {
        let config = AudioConfig::default();
        assert_eq!(config.sample_rate, 48000);
        assert_eq!(config.bitrate, 64000);
        assert_eq!(config.frame_size(), 960); // 48000 * 0.02 = 960 samples
    }

    #[test]
    fn test_low_latency_config() {
        let config = AudioConfig::low_latency();
        assert_eq!(config.frame_duration_ms, 10.0);
        assert_eq!(config.frame_size(), 480); // 48000 * 0.01 = 480 samples
    }

    #[test]
    fn test_opus_encode_decode() -> Result<()> {
        const TEST_FREQUENCY_HZ: f32 = 440.0;  // A4 note
        const SAMPLE_RATE: f32 = 48000.0;
        const AMPLITUDE_SCALE: f32 = 32767.0;  // Max i16 value
        
        let config = AudioConfig::low_latency();
        let frame_size = config.frame_size();
        
        let mut encoder = AudioEncoder::new(config.clone())?;
        let mut decoder = AudioDecoder::new(config)?;

        // Generate test audio (440Hz sine wave for testing)
        let pcm: Vec<i16> = (0..frame_size)
            .map(|i| (AMPLITUDE_SCALE * (2.0 * std::f32::consts::PI * TEST_FREQUENCY_HZ * i as f32 / SAMPLE_RATE).sin()) as i16)
            .collect();

        // Encode
        let encoded = encoder.encode(&pcm)?;
        assert!(!encoded.is_empty());
        assert!(encoded.len() < pcm.len() * 2); // Should be compressed

        // Decode
        let decoded = decoder.decode(&encoded)?;
        assert_eq!(decoded.len(), pcm.len());

        Ok(())
    }

    #[test]
    fn test_packet_loss_concealment() -> Result<()> {
        let config = AudioConfig::low_latency();
        let mut decoder = AudioDecoder::new(config.clone())?;

        // Simulate packet loss with PLC
        let plc_samples = decoder.decode_plc()?;
        assert_eq!(plc_samples.len(), config.frame_size());

        Ok(())
    }
}
