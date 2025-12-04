"""
Communication module for P2P chat, voice, and video streaming.

Note: These files are DEPRECATED reference implementations.
The actual P2P communication is handled by Go's libp2p implementation.
See docs/COMMUNICATION.md for details.
"""

from .live_chat import main as chat_main
from .live_voice import main as voice_main
from .live_video import main as video_main
