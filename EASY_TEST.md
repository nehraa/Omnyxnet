# Easy Cross-Device Testing

**One script. Both devices. Just run it.**

## Quick Start

```bash
./easy_test.sh
```

That's it! The script handles everything.

## How It Works

### Device 1 (Bootstrap)
1. Run `./easy_test.sh`
2. Press `Y`
3. Copy the peer address shown
4. Press ENTER when Device 2 is ready

### Device 2 (Join)
1. Run `./easy_test.sh`  
2. Press `N`
3. Paste the peer address from Device 1
4. Ready!

### Choose Your Test
- **1** - Audio Streaming (Opus codec, 20.87x compression)
- **2** - Video Streaming (HD compression, 19.14x)
- **3** - Text Messages
- **4** - File Transfer
- **5** - Run ALL tests

## What It Tests

- **Real P2P connection** between devices
- **Opus audio codec** with CES pipeline
- **Video compression** through CES
- **Cross-device communication** validation

## Requirements

- Both devices on same network (LAN/WiFi)
- Project built (`cd go && make build`)
- Python3 with numpy (for audio generation)

## That's It!

No complex setup. No configuration files. Just run and test.

Pull on other device and go:
```bash
git pull
./easy_test.sh
```
