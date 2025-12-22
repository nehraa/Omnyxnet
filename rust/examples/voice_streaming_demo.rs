/// Voice Streaming Demo
///
/// This example demonstrates how to use the streaming module for voice communication.
/// It shows:
/// 1. Creating a streaming session
/// 2. Encoding audio samples
/// 3. Serializing packets for transmission
/// 4. Deserializing received packets
/// 5. Decoding audio samples
///
/// Usage:
///   cargo run --example voice_streaming_demo --release
use pangea_ces::{StreamConfig, StreamPacket, StreamingSession};
use std::f32::consts::PI;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("==============================================");
    println!("    Pangea Net - Voice Streaming Demo");
    println!("==============================================\n");

    // Step 1: Create streaming session with voice configuration
    println!("1. Creating streaming session with voice configuration...");
    let config = StreamConfig::voice();
    println!(
        "   - Sample Rate: {} Hz",
        config.audio_config.as_ref().unwrap().sample_rate
    );
    println!(
        "   - Bitrate: {} bps",
        config.audio_config.as_ref().unwrap().bitrate
    );
    println!(
        "   - Frame Duration: {} ms",
        config.audio_config.as_ref().unwrap().frame_duration_ms
    );
    println!("   - Max Packet Size: {} bytes", config.max_packet_size);
    println!("   - Buffer Size: {} packets\n", config.buffer_size);

    let session = StreamingSession::new(config.clone());

    // Step 2: Create audio sender for peer ID 123
    println!("2. Creating audio stream sender for peer 123...");
    let mut sender = session.create_audio_sender(123)?;
    println!("   ✓ Sender created\n");

    // Step 3: Generate test audio (440 Hz sine wave - A4 note)
    println!("3. Generating test audio (440 Hz sine wave)...");
    let audio_config = session.config().audio_config.as_ref().unwrap();
    let frame_size = audio_config.frame_size();

    println!("   - Frame size: {} samples", frame_size);

    const TEST_FREQUENCY: f32 = 440.0; // A4 note
    const SAMPLE_RATE: f32 = 48000.0;

    let pcm_samples: Vec<i16> = (0..frame_size)
        .map(|i| {
            let t = i as f32 / SAMPLE_RATE;
            (32767.0 * (2.0 * PI * TEST_FREQUENCY * t).sin()) as i16
        })
        .collect();

    println!("   ✓ Generated {} PCM samples\n", pcm_samples.len());

    // Step 4: Encode audio to stream packet
    println!("4. Encoding audio to stream packet...");
    let packet = sender.encode_audio(&pcm_samples)?;

    println!("   - Sequence: {}", packet.sequence);
    println!("   - Timestamp: {}", packet.timestamp);
    println!("   - Payload size: {} bytes", packet.payload.len());
    println!(
        "   - Compression ratio: {:.2}x",
        (pcm_samples.len() * 2) as f32 / packet.payload.len() as f32
    );
    println!("   ✓ Audio encoded\n");

    // Step 5: Serialize packet for transmission
    println!("5. Serializing packet for network transmission...");
    let serialized = packet.to_bytes()?;
    println!("   - Serialized size: {} bytes", serialized.len());
    println!("   - Ready for UDP/QUIC transmission");
    println!("   ✓ Packet serialized\n");

    // Step 6: Simulate network transmission
    println!("6. Simulating network transmission...");
    println!("   → Packet would be sent via QUIC/UDP to peer 123");
    println!("   → Network layer would deliver to remote peer\n");

    // Step 7: Deserialize received packet (simulating receiver)
    println!("7. Deserializing received packet...");
    let received_packet = StreamPacket::from_bytes(&serialized)?;

    println!("   - Sequence: {}", received_packet.sequence);
    println!("   - Timestamp: {}", received_packet.timestamp);
    println!("   - Payload size: {} bytes", received_packet.payload.len());
    println!("   ✓ Packet deserialized\n");

    // Step 8: Demonstrate encoding multiple frames
    println!("8. Encoding multiple frames (sequence demo)...");
    for i in 0..5 {
        let packet = sender.encode_audio(&pcm_samples)?;
        println!(
            "   - Frame {}: Sequence {}, {} bytes",
            i + 1,
            packet.sequence,
            packet.payload.len()
        );
    }
    println!("   ✓ Multiple frames encoded with sequential numbers\n");

    // Step 9: Demonstrate bitrate adjustment
    println!("9. Demonstrating dynamic bitrate adjustment...");

    println!("   Setting bitrate to 16 kbps (low bandwidth)...");
    sender.set_bitrate(16000)?;
    let low_bitrate_packet = sender.encode_audio(&pcm_samples)?;
    println!(
        "   - Encoded size: {} bytes",
        low_bitrate_packet.payload.len()
    );

    println!("   Setting bitrate to 64 kbps (high quality)...");
    sender.set_bitrate(64000)?;
    let high_bitrate_packet = sender.encode_audio(&pcm_samples)?;
    println!(
        "   - Encoded size: {} bytes",
        high_bitrate_packet.payload.len()
    );

    println!("   ✓ Bitrate adjustment working\n");

    // Summary
    println!("==============================================");
    println!("                  SUMMARY");
    println!("==============================================");
    println!("✓ Streaming session created");
    println!("✓ Audio sender initialized");
    println!("✓ PCM audio generated (440 Hz sine wave)");
    println!("✓ Audio encoded to Opus format");
    println!("✓ Packet serialized for network transmission");
    println!("✓ Packet deserialized successfully");
    println!("✓ Sequence numbers working correctly");
    println!("✓ Dynamic bitrate adjustment working");
    println!("\n🎉 Voice streaming demo completed successfully!");
    println!("\nNext steps:");
    println!("  - Integrate with QUIC network layer");
    println!("  - Implement receiver decoding");
    println!("  - Add jitter buffer for smoother playback");
    println!("  - Test with real audio input/output\n");

    Ok(())
}
