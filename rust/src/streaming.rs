/// Real-time Streaming Module for Voice and Video Communication
///
/// This module provides UDP-based streaming capabilities using QUIC transport
/// for low-latency voice and video communication. It integrates with the existing
/// Opus audio codec and provides a foundation for future video streaming.
///
/// Architecture:
/// - Uses QUIC (UDP-based) for transport (already available via network.rs)
/// - Opus codec for audio encoding/decoding (from codecs.rs)
/// - Modular design for easy extension to video codecs
/// - Packet-based streaming with loss tolerance
///
/// Design Principles:
/// - Portability: Works across different platforms and networks
/// - Modularity: Separate concerns for audio, video, and transport
/// - Low latency: Optimized for real-time communication
/// - Resilience: Handles packet loss gracefully
use anyhow::{Context, Result};
use tokio::sync::mpsc;
use tracing::{debug, info, warn};

use crate::codecs::{AudioConfig, AudioDecoder, AudioEncoder};

/// Stream type identifier
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StreamType {
    /// Audio-only stream (voice)
    Audio,
    /// Video-only stream
    Video,
    /// Combined audio and video stream
    AudioVideo,
}

/// Streaming session configuration
#[derive(Debug, Clone)]
pub struct StreamConfig {
    /// Type of stream
    pub stream_type: StreamType,
    /// Audio configuration (required for Audio and AudioVideo streams)
    pub audio_config: Option<AudioConfig>,
    /// Maximum packet size in bytes
    pub max_packet_size: usize,
    /// Buffer size for incoming packets
    pub buffer_size: usize,
    /// Enable Forward Error Correction
    pub enable_fec: bool,
}

impl Default for StreamConfig {
    fn default() -> Self {
        Self {
            stream_type: StreamType::Audio,
            audio_config: Some(AudioConfig::low_latency()),
            max_packet_size: 1350, // Safe size for UDP/QUIC
            buffer_size: 100,
            enable_fec: true,
        }
    }
}

impl StreamConfig {
    /// Create configuration for voice streaming
    pub fn voice() -> Self {
        Self {
            stream_type: StreamType::Audio,
            audio_config: Some(AudioConfig::low_latency()),
            max_packet_size: 1350,
            buffer_size: 50, // Smaller buffer for lower latency
            enable_fec: true,
        }
    }

    /// Create configuration for high-quality audio streaming
    pub fn audio_hq() -> Self {
        Self {
            stream_type: StreamType::Audio,
            audio_config: Some(AudioConfig::high_quality()),
            max_packet_size: 1350,
            buffer_size: 100,
            enable_fec: true,
        }
    }
}

/// Stream packet for transmission
#[derive(Debug, Clone)]
pub struct StreamPacket {
    /// Sequence number for ordering and loss detection
    pub sequence: u64,
    /// Timestamp in milliseconds
    pub timestamp: u64,
    /// Stream type identifier
    pub stream_type: StreamType,
    /// Encoded payload data
    pub payload: Vec<u8>,
    /// Forward Error Correction data (if enabled)
    pub fec_data: Option<Vec<u8>>,
}

impl StreamPacket {
    /// Serialize packet to bytes for transmission
    pub fn to_bytes(&self) -> Result<Vec<u8>> {
        // Simple serialization format:
        // [8 bytes: sequence][8 bytes: timestamp][1 byte: stream_type]
        // [4 bytes: payload_len][payload][4 bytes: fec_len][fec_data]

        let mut buffer = Vec::new();
        buffer.extend_from_slice(&self.sequence.to_be_bytes());
        buffer.extend_from_slice(&self.timestamp.to_be_bytes());

        let stream_type_byte = match self.stream_type {
            StreamType::Audio => 0u8,
            StreamType::Video => 1u8,
            StreamType::AudioVideo => 2u8,
        };
        buffer.push(stream_type_byte);

        buffer.extend_from_slice(&(self.payload.len() as u32).to_be_bytes());
        buffer.extend_from_slice(&self.payload);

        if let Some(fec) = &self.fec_data {
            buffer.extend_from_slice(&(fec.len() as u32).to_be_bytes());
            buffer.extend_from_slice(fec);
        } else {
            buffer.extend_from_slice(&0u32.to_be_bytes());
        }

        Ok(buffer)
    }

    /// Deserialize packet from bytes
    pub fn from_bytes(data: &[u8]) -> Result<Self> {
        if data.len() < 21 {
            anyhow::bail!("Packet too small: {} bytes", data.len());
        }

        let sequence = u64::from_be_bytes(data[0..8].try_into()?);
        let timestamp = u64::from_be_bytes(data[8..16].try_into()?);

        let stream_type = match data[16] {
            0 => StreamType::Audio,
            1 => StreamType::Video,
            2 => StreamType::AudioVideo,
            _ => anyhow::bail!("Invalid stream type: {}", data[16]),
        };

        let payload_len = u32::from_be_bytes(data[17..21].try_into()?) as usize;
        if data.len() < 21 + payload_len + 4 {
            anyhow::bail!("Incomplete packet data");
        }

        let payload = data[21..21 + payload_len].to_vec();
        let fec_len_start = 21 + payload_len;
        let fec_len =
            u32::from_be_bytes(data[fec_len_start..fec_len_start + 4].try_into()?) as usize;

        let fec_data = if fec_len > 0 {
            Some(data[fec_len_start + 4..fec_len_start + 4 + fec_len].to_vec())
        } else {
            None
        };

        Ok(StreamPacket {
            sequence,
            timestamp,
            stream_type,
            payload,
            fec_data,
        })
    }
}

/// Audio stream sender
pub struct AudioStreamSender {
    encoder: AudioEncoder,
    sequence: u64,
    #[allow(dead_code)]
    config: StreamConfig,
    peer_id: u32,
}

impl AudioStreamSender {
    /// Create a new audio stream sender
    pub fn new(config: StreamConfig, peer_id: u32) -> Result<Self> {
        let audio_config = config
            .audio_config
            .clone()
            .context("Audio config required for audio stream")?;

        let encoder = AudioEncoder::new(audio_config)?;

        info!(
            "Created audio stream sender for peer {} with config: {:?}",
            peer_id, config
        );

        Ok(Self {
            encoder,
            sequence: 0,
            config,
            peer_id,
        })
    }

    /// Encode audio frame
    ///
    /// # Arguments
    /// * `pcm_samples` - Raw PCM audio samples (16-bit signed integers)
    ///
    /// Returns the encoded packet ready for transmission via the network layer
    pub fn encode_audio(&mut self, pcm_samples: &[i16]) -> Result<StreamPacket> {
        // Encode audio to Opus
        let encoded = self
            .encoder
            .encode(pcm_samples)
            .context("Failed to encode audio")?;

        let encoded_len = encoded.len();

        // Create stream packet
        let packet = StreamPacket {
            sequence: self.sequence,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)?
                .as_millis() as u64,
            stream_type: StreamType::Audio,
            payload: encoded,
            fec_data: None, // TODO: Add FEC if enabled
        };

        self.sequence += 1;

        debug!(
            "Encoded audio packet {} ({} bytes)",
            packet.sequence, encoded_len
        );

        Ok(packet)
    }

    /// Get the target peer ID
    pub fn peer_id(&self) -> u32 {
        self.peer_id
    }

    /// Set encoder bitrate dynamically based on network conditions
    pub fn set_bitrate(&mut self, bitrate: i32) -> Result<()> {
        self.encoder.set_bitrate(bitrate)
    }
}

/// Audio stream receiver
pub struct AudioStreamReceiver {
    decoder: AudioDecoder,
    last_sequence: u64,
    #[allow(dead_code)]
    config: StreamConfig,
    packet_rx: mpsc::Receiver<StreamPacket>,
}

impl AudioStreamReceiver {
    /// Create a new audio stream receiver
    pub fn new(config: StreamConfig, packet_rx: mpsc::Receiver<StreamPacket>) -> Result<Self> {
        let audio_config = config
            .audio_config
            .clone()
            .context("Audio config required for audio stream")?;

        let decoder = AudioDecoder::new(audio_config)?;

        info!("Created audio stream receiver with config: {:?}", config);

        Ok(Self {
            decoder,
            last_sequence: 0,
            config,
            packet_rx,
        })
    }

    /// Receive and decode audio frame
    ///
    /// Returns PCM samples or None if no packet available
    pub async fn receive_audio(&mut self) -> Result<Option<Vec<i16>>> {
        match self.packet_rx.recv().await {
            Some(packet) => {
                // Check for packet loss
                if packet.sequence > self.last_sequence + 1 {
                    let lost = packet.sequence - self.last_sequence - 1;
                    warn!(
                        "Lost {} audio packets (seq {} -> {})",
                        lost, self.last_sequence, packet.sequence
                    );

                    // Use Packet Loss Concealment for first lost packet
                    if lost == 1 {
                        let plc_samples = self.decoder.decode_plc()?;
                        debug!(
                            "Generated {} PLC samples for lost packet",
                            plc_samples.len()
                        );
                    }
                }

                self.last_sequence = packet.sequence;

                // Decode audio
                let pcm = self
                    .decoder
                    .decode(&packet.payload)
                    .context("Failed to decode audio packet")?;

                debug!(
                    "Received and decoded audio packet {} ({} samples)",
                    packet.sequence,
                    pcm.len()
                );

                Ok(Some(pcm))
            }
            None => Ok(None),
        }
    }
}

/// Streaming session manager
pub struct StreamingSession {
    config: StreamConfig,
}

impl StreamingSession {
    /// Create a new streaming session
    pub fn new(config: StreamConfig) -> Self {
        info!("Created streaming session: {:?}", config);

        Self { config }
    }

    /// Create audio sender for this session
    pub fn create_audio_sender(&self, peer_id: u32) -> Result<AudioStreamSender> {
        AudioStreamSender::new(self.config.clone(), peer_id)
    }

    /// Create audio receiver for this session
    pub fn create_audio_receiver(&self) -> Result<AudioStreamReceiver> {
        let (_packet_tx, packet_rx) = mpsc::channel(self.config.buffer_size);

        // Note: In a real implementation, the network layer would feed packets
        // into packet_tx. For now, this is a placeholder that applications
        // can integrate with their network transport.

        AudioStreamReceiver::new(self.config.clone(), packet_rx)
    }

    /// Get session configuration
    pub fn config(&self) -> &StreamConfig {
        &self.config
    }
}

/// Streaming statistics
#[derive(Debug, Clone, Default)]
pub struct StreamStats {
    pub packets_sent: u64,
    pub packets_received: u64,
    pub packets_lost: u64,
    pub average_latency_ms: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stream_packet_serialization() -> Result<()> {
        let packet = StreamPacket {
            sequence: 42,
            timestamp: 1234567890,
            stream_type: StreamType::Audio,
            payload: vec![1, 2, 3, 4, 5],
            fec_data: Some(vec![6, 7, 8]),
        };

        let bytes = packet.to_bytes()?;
        let decoded = StreamPacket::from_bytes(&bytes)?;

        assert_eq!(packet.sequence, decoded.sequence);
        assert_eq!(packet.timestamp, decoded.timestamp);
        assert_eq!(packet.stream_type, decoded.stream_type);
        assert_eq!(packet.payload, decoded.payload);
        assert_eq!(packet.fec_data, decoded.fec_data);

        Ok(())
    }

    #[test]
    fn test_stream_config_defaults() {
        let config = StreamConfig::voice();
        assert_eq!(config.stream_type, StreamType::Audio);
        assert!(config.audio_config.is_some());
        assert_eq!(config.max_packet_size, 1350);
    }
}
