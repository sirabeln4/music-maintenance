"""Read-only MP3/WMA scanner used by the prototype."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from mutagen import File
from mutagen.id3 import ID3
from mutagen.asf import ASF
from .catalog_db import CatalogDatabase

def _tag(audio: object, name: str) -> str:
    value = getattr(audio, "tags", {}).get(name, "") if audio else ""
    if isinstance(value, (list, tuple)): value = value[0] if value else ""
    return str(value or "")

def _artwork_state(audio: object, raw_audio: object) -> str:
    """Detect common embedded-art frames for MP3 and WMA/ASF files."""
    if getattr(audio, "pictures", None):
        return "Present"
    tags = getattr(raw_audio, "tags", None) or {}
    for key in tags:
        key_text = str(key).upper()
        if key_text.startswith("APIC") or key_text == "WM/PICTURE":
            return "Present"
    return "Missing"

def artwork_bytes(path: Path) -> bytes | None:
    try:
        if path.suffix.lower() == ".mp3":
            pictures = ID3(path).getall("APIC")
            return pictures[0].data if pictures else None
        tags = ASF(path).tags or {}
        for picture in tags.get("WM/Picture", []):
            data = getattr(picture, "value", None) or getattr(picture, "data", None)
            if isinstance(data, bytes):
                return data
    except Exception:
        return None
    return None

def scan_paths(paths: list[Path], recursive: bool, database: CatalogDatabase, progress, cancel: Event | None = None) -> tuple[int, int, bool]:
    files = []
    for root in paths:
        if root.exists():
            iterator = root.rglob("*") if recursive else root.glob("*")
            files.extend(p for p in iterator if p.is_file() and p.suffix.lower() in {".mp3", ".wma"})
    scanned = failed = 0
    seen: set[str] = set()
    now = datetime.now(timezone.utc).isoformat()
    for path in files:
        if cancel and cancel.is_set():
            database.commit()
            progress("", scanned, len(files))
            return scanned, failed, True
        seen.add(str(path))
        progress(str(path), scanned, len(files))
        try:
            stat = path.stat()
            previous = database.signature_for_path(str(path))
            if previous and previous["size"] == stat.st_size and previous["modified_ns"] == stat.st_mtime_ns:
                scanned += 1
                continue
            audio = File(path, easy=True)
            raw_audio = File(path, easy=False)
            info = getattr(audio, "info", None)
            values = {"path": str(path), "filename": path.name, "extension": path.suffix.lower(), "size": stat.st_size, "modified_ns": stat.st_mtime_ns, "scan_time": now, "available": 1, "status": "File", "issue": None, "artist": _tag(audio, "artist"), "album_artist": _tag(audio, "albumartist"), "album": _tag(audio, "album"), "title": _tag(audio, "title"), "track": _tag(audio, "tracknumber"), "year": _tag(audio, "date"), "genre": _tag(audio, "genre"), "duration": getattr(info, "length", None), "bitrate": getattr(info, "bitrate", None), "sample_rate": getattr(info, "sample_rate", None), "artwork_state": _artwork_state(audio, raw_audio)}
            database.upsert_file(values)
        except Exception as exc:
            failed += 1
            stat = path.stat() if path.exists() else None
            database.upsert_file({"path": str(path), "filename": path.name, "extension": path.suffix.lower(), "size": stat.st_size if stat else None, "modified_ns": stat.st_mtime_ns if stat else None, "scan_time": now, "available": 1, "issue": f"Read failed: {exc}"})
        scanned += 1
    database.mark_missing_under(paths, seen)
    database.commit(); progress("", scanned, len(files))
    return scanned, failed, False
