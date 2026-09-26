"""Cover Art Archive client for review-only artwork selection."""
from __future__ import annotations
import json
import certifi
import ssl
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def release_images(release_id: str) -> list[dict]:
    if not release_id: return []
    request = Request(f"https://coverartarchive.org/release/{release_id}", headers={"User-Agent": "MusicMaintenance/0.1"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=15, context=context) as response:
        data = json.load(response)
    def secure(url):
        return url.replace("http://", "https://") if url else url
    return [{"types": ", ".join(image.get("types", [])), "front": image.get("front", False), "width": image.get("width"), "height": image.get("height"), "url": secure(image.get("image")), "thumb": secure(image.get("thumbnails", {}).get("large") or image.get("image"))} for image in data.get("images", [])]

def itunes_images(artist: str, album: str, title: str = "") -> list[dict]:
    """Return reviewable album artwork from Apple's free Search API."""
    term = " ".join(value.strip() for value in (artist or "", album or "") if value and value.strip())
    if not term: return []
    query = urlencode({"term": term, "entity": "album", "limit": 5})
    request = Request(f"https://itunes.apple.com/search?{query}", headers={"User-Agent": "MusicMaintenance/0.6"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=15, context=context) as response:
        data = json.load(response)
    results = []
    for item in data.get("results", []):
        thumb = item.get("artworkUrl100")
        if not thumb: continue
        url = thumb.replace("100x100", "600x600")
        results.append({"source": "itunes", "types": "Apple album artwork", "front": True, "width": None, "height": None, "url": url, "thumb": thumb, "artist": item.get("artistName"), "album": item.get("collectionName")})
    return results
