"""Small MusicBrainz lookup client for review-only proposals."""
from __future__ import annotations
import json
import certifi
import ssl
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def search_recordings(artist: str, title: str, album: str = "") -> list[dict]:
    terms = []
    if artist: terms.append(f'artist:"{artist}"')
    if title: terms.append(f'recording:"{title}"')
    if album: terms.append(f'release:"{album}"')
    query = " AND ".join(terms)
    if not query: return []
    url = "https://musicbrainz.org/ws/2/recording?" + urlencode({"query": query, "fmt": "json", "limit": 10, "inc": "artist-credits+releases+release-groups+genres+media+labels+recording-level-rels+work-level-rels"})
    request = Request(url, headers={"User-Agent": "MusicMaintenance/0.1 (prototype)"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=15, context=context) as response:
        data = json.load(response)
    results = []
    for item in data.get("recordings", []):
        releases = item.get("releases", [])
        release = releases[0] if releases else {}
        groups = release.get("release-group", {}) or {}
        labels = [label.get("label", {}).get("name", "") for label in release.get("label-info", []) if label.get("label")]
        credited_artist = ", ".join(a.get("name", "") for a in item.get("artist-credit", []))
        media = release.get("media", []) or []
        works = [relation.get("work", {}).get("title", "") for relation in item.get("relations", []) if relation.get("type") == "performance" and relation.get("work")]
        results.append({"title": item.get("title", ""), "artist": ", ".join(a.get("name", "") for a in item.get("artist-credit", [])), "release": release.get("title", ""), "release_group": groups.get("title", ""), "date": release.get("date", ""), "country": release.get("country", ""), "status": release.get("status", ""), "barcode": release.get("barcode", ""), "label": ", ".join(labels), "media": [{"format": m.get("format", ""), "tracks": m.get("track-count"), "position": m.get("position")} for m in media], "genres": [genre.get("name", "") for genre in item.get("genres", [])], "works": works, "length": item.get("length"), "disambiguation": item.get("disambiguation", ""), "score": item.get("score", 0), "recording_id": item.get("id", ""), "artist_ids": [a.get("artist", {}).get("id", "") for a in item.get("relations", []) if a.get("artist")], "release_id": release.get("id", ""), "release_group_id": groups.get("id", "")})
    return results

def recordings_by_ids(recording_ids: list[str]) -> list[dict]:
    results = []
    context = ssl.create_default_context(cafile=certifi.where())
    for recording_id in dict.fromkeys(recording_ids):
        if not recording_id: continue
        url = "https://musicbrainz.org/ws/2/recording/" + recording_id + "?" + urlencode({"fmt": "json", "inc": "artist-credits+releases+release-groups+genres+media+labels+recording-level-rels+work-level-rels"})
        request = Request(url, headers={"User-Agent": "MusicMaintenance/0.10"})
        with urlopen(request, timeout=15, context=context) as response: item = json.load(response)
        releases = item.get("releases", []); release = releases[0] if releases else {}; groups = release.get("release-group", {}) or {}; credited_artist = ", ".join(a.get("name", "") for a in item.get("artist-credit", []))
        results.append({"title": item.get("title", ""), "artist": credited_artist, "album_artist": credited_artist, "release": release.get("title", ""), "release_group": groups.get("title", ""), "date": release.get("date", ""), "country": release.get("country", ""), "status": release.get("status", ""), "barcode": release.get("barcode", ""), "label": ", ".join(x.get("label", {}).get("name", "") for x in release.get("label-info", []) if x.get("label")), "genres": [x.get("name", "") for x in item.get("genres", [])], "length": item.get("length"), "disambiguation": item.get("disambiguation", ""), "score": 100, "recording_id": item.get("id", ""), "release_id": release.get("id", ""), "release_group_id": groups.get("id", "")})
    return results
