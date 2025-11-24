/// Tests for UDP-based voice and video streaming
///
/// These tests validate the streaming module's functionality including:
/// - Audio encoding/decoding with Opus
/// - Stream packet serialization
/// - Session management

use pangea_ces::{
    AudioConfig, StreamConfig, StreamType, StreamingSession,
    AudioStreamSender, AudioStreamReceiver, StreamPacket,
};
use anyhow::Result;

#[test]
fn test_stream_config_voice() {
    let config = StreamConfig::voice();
    assert_eq!(config.stream_type, StreamType::Audio);
    assert!(config.audio_config.is_some());
    assert_eq!(config.max_packet_size, 1350);
    assert_eq!(config.buffer_size, 50);
    assert!(config.enable_fec);
}

#[test]
fn test_stream_config_audio_hq() {
    let config = StreamConfig::audio_hq();
    assert_eq!(config.stream_type, StreamType::Audio);
    assert!(config.audio_config.is_some());
    
    // High quality should use better audio config
    let audio_config = config.audio_config.unwrap();
    assert_eq!(audio_config.bitrate, 128000);
}

#[test]
fn test_streaming_session_creation() {
    let config = StreamConfig::voice();
    let session = StreamingSession::new(config.clone());
    
    // Verify config is accessible
    assert_eq!(session.config().stream_type, StreamType::Audio);
}

#[test]
fn test_audio_stream_sender_creation() -> Result<()> {
    let config = StreamConfig::voice();
    let sender = AudioStreamSender::new(config, 123)?;
    
    assert_eq!(sender.peer_id(), 123);
    Ok(())
}

#[test]
fn test_audio_encoding() -> Result<()> {
    let config = StreamConfig::voice();
    let audio_config = config.audio_config.clone().unwrap();
    let frame_size = audio_config.frame_size();
    
    let mut sender = AudioStreamSender::new(config, 1)?;
    
    // Generate test audio (sine wave at 440Hz)
    const TEST_FREQUENCY_HZ: f32 = 440.0;
    const SAMPLE_RATE: f32 = 48000.0;
    const AMPLITUDE_SCALE: f32 = 32767.0;
    
    let pcm: Vec<i16> = (0..frame_size)
        .map(|i| {
            (AMPLITUDE_SCALE * (2.0 * std::f32::consts::PI * TEST_FREQUENCY_HZ * i as f32 / SAMPLE_RATE).sin()) as i16
        })
        .collect();
    
    // Encode audio
    let packet = sender.encode_audio(&pcm)?;
    
    // Verify packet properties
    assert_eq!(packet.sequence, 0);
    assert_eq!(packet.stream_type, StreamType::Audio);
    assert!(!packet.payload.is_empty());
    assert!(packet.payload.len() < pcm.len() * 2); // Should be compressed
    
    Ok(())
}

#[test]
fn test_audio_encoding_sequence() -> Result<()> {
    let config = StreamConfig::voice();
    let audio_config = config.audio_config.clone().unwrap();
    let frame_size = audio_config.frame_size();
    
    let mut sender = AudioStreamSender::new(config, 1)?;
    
    // Generate silent audio
    let pcm: Vec<i16> = vec![0; frame_size];
    
    // Encode multiple frames
    let packet1 = sender.encode_audio(&pcm)?;
    let packet2 = sender.encode_audio(&pcm)?;
    let packet3 = sender.encode_audio(&pcm)?;
    
    // Verify sequence numbers increment
    assert_eq!(packet1.sequence, 0);
    assert_eq!(packet2.sequence, 1);
    assert_eq!(packet3.sequence, 2);
    
    Ok(())
}

#[test]
fn test_stream_packet_serialization_audio() -> Result<()> {
    let packet = StreamPacket {
        sequence: 42,
        timestamp: 1234567890,
        stream_type: StreamType::Audio,
        payload: vec![1, 2, 3, 4, 5],
        fec_data: None,
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
fn test_stream_packet_serialization_with_fec() -> Result<()> {
    let packet = StreamPacket {
        sequence: 100,
        timestamp: 9876543210,
        stream_type: StreamType::Audio,
        payload: vec![10, 20, 30, 40, 50],
        fec_data: Some(vec![60, 70, 80]),
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
fn test_stream_packet_video_type() -> Result<()> {
    let packet = StreamPacket {
        sequence: 1,
        timestamp: 1000,
        stream_type: StreamType::Video,
        payload: vec![1, 2, 3],
        fec_data: None,
    };
    
    let bytes = packet.to_bytes()?;
    let decoded = StreamPacket::from_bytes(&bytes)?;
    
    assert_eq!(decoded.stream_type, StreamType::Video);
    
    Ok(())
}

#[test]
fn test_audio_receiver_creation() -> Result<()> {
    let config = StreamConfig::voice();
    let session = StreamingSession::new(config);
    
    // Create receiver
    let _receiver = session.create_audio_receiver()?;
    
    Ok(())
}

#[test]
fn test_bitrate_adjustment() -> Result<()> {
    let config = StreamConfig::voice();
    let mut sender = AudioStreamSender::new(config, 1)?;
    
    // Adjust bitrate
    sender.set_bitrate(64000)?;
    
    Ok(())
}

#[test]
fn test_stream_types() {
    assert_eq!(StreamType::Audio, StreamType::Audio);
    assert_ne!(StreamType::Audio, StreamType::Video);
    assert_ne!(StreamType::Audio, StreamType::AudioVideo);
}
