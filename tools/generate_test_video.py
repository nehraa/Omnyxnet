#!/usr/bin/env python3
"""
Generate a simple test video for DCDN streaming demonstrations.

This script creates a test video with:
- Colored frames that cycle through different colors
- Frame counter overlay
- Timestamp display
- Resolution and FPS settings suitable for streaming

The generated video can be used to test DCDN streaming functionality
and verify that video data is being transmitted and received correctly.

Requirements:
- opencv-python (cv2)
- numpy

Usage:
    python tools/generate_test_video.py [output_path] [duration_seconds]

Example:
    python tools/generate_test_video.py test_video.mp4 10
"""

import sys
import argparse
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install opencv-python numpy")
    sys.exit(1)


def generate_test_video(
    output_path: str,
    duration: int = 10,
    fps: int = 30,
    width: int = 640,
    height: int = 480,
):
    """
    Generate a test video with colored frames and overlays.

    Args:
        output_path: Path where the video will be saved
        duration: Video duration in seconds
        fps: Frames per second
        width: Video width in pixels
        height: Video height in pixels
    """
    print(f"Generating test video: {output_path}")
    print(f"Duration: {duration}s, FPS: {fps}, Resolution: {width}x{height}")

    # Define video codec and create VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not out.isOpened():
        print("Error: Could not open video writer")
        return False

    # Color cycle (BGR format)
    colors = [
        (255, 0, 0),  # Blue
        (0, 255, 0),  # Green
        (0, 0, 255),  # Red
        (255, 255, 0),  # Cyan
        (255, 0, 255),  # Magenta
        (0, 255, 255),  # Yellow
        (255, 255, 255),  # White
        (128, 128, 128),  # Gray
    ]

    total_frames = duration * fps

    for frame_num in range(total_frames):
        # Create a blank frame
        color_idx = (frame_num // fps) % len(colors)
        color = colors[color_idx]
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = color

        # Add gradient effect
        gradient = np.linspace(0, 1, width, dtype=np.float32)
        for c in range(3):
            frame[:, :, c] = (frame[:, :, c] * gradient).astype(np.uint8)

        # Add text overlays
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Title
        title = "DCDN Test Video"
        cv2.putText(frame, title, (width // 2 - 150, 60), font, 1.2, (0, 0, 0), 3)
        cv2.putText(frame, title, (width // 2 - 150, 60), font, 1.2, (255, 255, 255), 2)

        # Frame counter
        frame_text = f"Frame: {frame_num + 1}/{total_frames}"
        cv2.putText(frame, frame_text, (20, height - 60), font, 0.8, (0, 0, 0), 3)
        cv2.putText(frame, frame_text, (20, height - 60), font, 0.8, (255, 255, 255), 2)

        # Timestamp
        time_text = f"Time: {frame_num/fps:.2f}s"
        cv2.putText(frame, time_text, (20, height - 20), font, 0.8, (0, 0, 0), 3)
        cv2.putText(frame, time_text, (20, height - 20), font, 0.8, (255, 255, 255), 2)

        # Color indicator
        color_name = [
            "Blue",
            "Green",
            "Red",
            "Cyan",
            "Magenta",
            "Yellow",
            "White",
            "Gray",
        ][color_idx]
        color_text = f"Color: {color_name}"
        cv2.putText(
            frame, color_text, (width - 250, height - 20), font, 0.8, (0, 0, 0), 3
        )
        cv2.putText(
            frame, color_text, (width - 250, height - 20), font, 0.8, (255, 255, 255), 2
        )

        # Add a moving circle
        circle_x = int(width * ((frame_num % fps) / fps))
        circle_y = height // 2
        cv2.circle(frame, (circle_x, circle_y), 30, (0, 0, 0), -1)
        cv2.circle(frame, (circle_x, circle_y), 25, (255, 255, 255), -1)

        # Write frame to video
        out.write(frame)

        # Progress indicator
        if (frame_num + 1) % fps == 0:
            print(
                f"Progress: {frame_num + 1}/{total_frames} frames ({(frame_num + 1)/total_frames*100:.1f}%)"
            )

    out.release()

    # Verify the video was created
    file_size = Path(output_path).stat().st_size
    print("\n✅ Video generated successfully!")
    print(f"   Output: {output_path}")
    print(f"   Size: {file_size / (1024*1024):.2f} MB")
    print(f"   Frames: {total_frames}")
    print(f"   Duration: {duration}s")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate a test video for DCDN streaming demonstrations"
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="test_video.mp4",
        help="Output video file path (default: test_video.mp4)",
    )
    parser.add_argument(
        "duration",
        nargs="?",
        type=int,
        default=10,
        help="Video duration in seconds (default: 10)",
    )
    parser.add_argument(
        "--fps", type=int, default=30, help="Frames per second (default: 30)"
    )
    parser.add_argument(
        "--width", type=int, default=640, help="Video width in pixels (default: 640)"
    )
    parser.add_argument(
        "--height", type=int, default=480, help="Video height in pixels (default: 480)"
    )

    args = parser.parse_args()

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    success = generate_test_video(
        str(output_path),
        duration=args.duration,
        fps=args.fps,
        width=args.width,
        height=args.height,
    )

    if not success:
        sys.exit(1)

    # Get relative path from project root
    project_root = Path(__file__).parent.parent
    video_script = project_root / "python" / "src" / "communication" / "live_video.py"

    print("\nYou can now use this video for DCDN streaming tests:")
    print(f"  Desktop App: Browse to {output_path} in the DCDN tab")
    if video_script.exists():
        print(f"  Command Line: python {video_script} [server|peer_ip]")
    else:
        print(
            "  Command Line: Check python/src/communication/live_video.py for video streaming"
        )


if __name__ == "__main__":
    main()
