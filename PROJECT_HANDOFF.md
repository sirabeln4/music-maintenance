# Music Maintenance Project Handoff

Updated: 2026-09-07
Current version: **0.13.1**

## Resume instructions

Open this project folder and read this file first, then read [MUSIC_MAINTENANCE_DESIGN.md](MUSIC_MAINTENANCE_DESIGN.md). The application is a Windows desktop PySide6 prototype for MP3/WMA files in Google Drive for desktop, normally `G:\My Drive\Music`.

Run it from the project root with:

```powershell
.venv\Scripts\python.exe -m music_maintenance.app
```

The virtual environment contains PySide6, Mutagen, certifi, and pyacoustid. `fpcalc.exe` is configured through Settings. FFmpeg is also configured through Settings for WMA conversion.

## Completed functionality

- SQLite catalog with incremental scan and persisted metadata.
- MP3/WMA scanning, issue filtering, search, column ordering, and sort settings.
- Google Drive mapped-path handling and unavailable-file reporting.
- MusicBrainz tag-based lookup with retries and a threaded batch lookup dialog.
- AcoustID fingerprint lookup through pyacoustid and fpcalc, followed by MusicBrainz recording lookup.
- Extended MusicBrainz candidate evidence: release group, genre, label, barcode, media, works, and IDs.
- Candidate comparison and metadata proposal editing.
- Per-field `Use current` controls.
- Artwork review with embedded artwork, Cover Art Archive, Apple fallback, local images, thumbnails, dimensions, URL/error status, and placeholder choice.
- Review plans, pending/applied/result statuses, plan locking after apply, archiving, and plan history.
- MP3 metadata and artwork application with backup, verification, and Undo last apply.
- Windows-safe destination calculation, album-artist/album folders, filename collision suffixes, and move tracking.
- WMA-to-MP3 conversion using the WMA bitrate, metadata copy, progress popup, Google Drive hydration wait, and WMA conversion backup.
- Folder-first catalog view: selecting folders filters the table to those folders and descendants while using SQLite-backed metadata; clearing folder selection returns to the full catalog.
- Expandable folder tree for browsing available subfolders; tree selection controls the catalog view without starting a scan.

## Important current limitations

- WMA artwork embedding is not implemented; WMA text-tag conversion is available.
- AcoustID results are integrated for lookup, but fingerprint IDs are not yet written into file tags.
- Conversion and some artwork operations still run synchronously in the UI thread.
- Conversion currently starts MusicBrainz confirmation manually after the MP3 is created.
- Filename/folder destination is shown in active-plan review, but collision resolution is finalized during apply.
- Plan item result statuses are stored, but the active-plan summary and archive cleanup UI can be improved.
- Undo currently restores the last apply backup; retention cleanup is time-based and should be tested carefully.
- Google Drive may change streamed file timestamps, causing revalidation skips.
- The project has not yet been packaged as a portable executable.

## Recommended remaining sequence

1. Add WMA ASF artwork embedding and post-save verification.
2. Make conversion and artwork/network work fully threaded with cancelable workers.
3. Add automatic post-conversion MusicBrainz/AcoustID confirmation.
4. Add a final destination/collision preview immediately before apply.
5. Improve per-plan summary, item history, and backup/Undo retention management.
6. Add playlist creation and SD-card export for the Kinobo A12 after playback-order testing.
7. Add portable packaging and test on both laptops.

## Safety rules to preserve

- Never change files without an explicit reviewed plan approval.
- Preserve existing tags unless a reviewed proposal changes them.
- Keep current embedded artwork when selected.
- Revalidate size and modified time before applying.
- Back up before writing or moving.
- Keep failed or skipped items visible and actionable.
- Do not permanently delete duplicates; Google Drive Trash is the intended deletion path.

## Key files

- `src/music_maintenance/app.py` — PySide6 UI and workflow.
- `src/music_maintenance/catalog_db.py` — SQLite catalog and plan persistence.
- `src/music_maintenance/musicbrainz.py` — MusicBrainz requests and candidate parsing.
- `src/music_maintenance/coverart.py` — Cover Art Archive and Apple artwork lookup.
- `src/music_maintenance/converter.py` — WMA-to-MP3 conversion.
- `src/music_maintenance/scanner.py` — MP3/WMA scanning and artwork detection.
- `MUSIC_MAINTENANCE_DESIGN.md` — business rules and design decisions.
- `AI_README.md` — older project instructions; do not treat it as the current design.

Before making changes, confirm the current version in `src/music_maintenance/__init__.py` and run:

```powershell
.venv\Scripts\python.exe -m compileall -q src
```
