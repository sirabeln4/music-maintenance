"""WMA to MP3 conversion helpers."""
from __future__ import annotations
import subprocess
from pathlib import Path
from mutagen import File

def convert_wma_to_mp3(source: Path, ffmpeg: str = "ffmpeg") -> Path:
    audio = File(source, easy=True)
    bitrate = int(getattr(getattr(audio, "info", None), "bitrate", 192000) or 192000) // 1000
    bitrate = max(32, min(320, bitrate))
    target = source.with_suffix(".mp3")
    if target.exists(): raise FileExistsError(target)
    command = [ffmpeg, "-y", "-i", str(source), "-map_metadata", "0", "-codec:a", "libmp3lame", "-b:a", f"{bitrate}k", str(target)]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return target
