# Music Maintenance: Rules and Starting Design

Last updated: 2026-09-04

Status: Initial design for discussion; implementation has not started.

## 1. Purpose and decision status

Build a program that helps inspect, identify, tag, illustrate, and organize a personal MP3/WMA collection on a Google Drive mounted in Windows as `G:`.

The previous project's `AI_README.md` supplies historical preferences. This document extracts the reusable rules and proposes a design for a maintained application. Historical artist counts and cleanup results are not current inventory or evidence that a particular file is correct.

Confirmed for this project:

- Support MP3 and WMA only in the first version, including metadata, artwork, and the actual audio. Other file types may be counted in an inventory but are not inspected or changed.
- Keep full music names in tags while translating filenames into Windows-compatible names.
- Provide a Windows desktop application only, local drive access, and online music lookup.
- Show proposed changes and apply only the changes selected by the user. Do not apply changes automatically, even for confident matches.
- The collection is cloud-only, accessed online through the mapped `G:` drive.
- User-reported collection size: approximately 60 GB, 18,844 files, and 5,660 folders. These are total collection counts, not a verified count of audio files; images and other files may be included.
- Current playback targets: Windows Media Player 11.2607.16.0 on this PC; VLC on the user's phone; and the user's wife's Kinobo A12 Bluetooth headphones, which play MP3 files from a TF (microSD) card.
- Develop the design through interviews before building the application.
- Ask interview questions one at a time. Preserve unanswered questions rather than treating them as decisions or moving past them without explanation.

Inherited preferences below are starting defaults, not newly confirmed decisions. New recommendations are explicitly called proposals. Unanswered questions remain open; they do not authorize changes to the collection.

Confirmed library root: `G:\My Drive\Music`. The application should still let the user select a different root when needed.

## 2. Rules retained from the old project

- Inventory before editing. Treat filenames, folders, and existing tags as clues, not proof.
- Preserve uncertainty. Do not invent artists, release assignments, track numbers, dates, or artwork.
- When evidence establishes that an existing tag value is wrong but does not establish a correct replacement, propose clearing that field. Show every cleared field in the review; never clear tags automatically.
- Preserve official spelling, punctuation, Unicode, and featured-artist credits in tags.
- Use the complete track-artist credit, including featured artists, in filenames; keep album artist as a separate field and use it for the folder path.
- Preserve meaningful version labels: clean, explicit, remix, live, single edit, alternate, and unreleased.
- Review proposed corrections and apply only selected changes (confirmed for this project). An approved batch should not require a separate prompt for every file.
- Never overwrite another recording to resolve a filename collision. Use `(1)`, `(2)`, and subsequent numeric suffixes when known duplicates need distinct filenames.
- Never delete audio automatically. Use a dedicated, user-selected duplicate-cleanup process to review and delete unneeded copies.
- Do not transcode as part of tagging or renaming. Increasing a bitrate does not recover lost quality. When a low-quality file is the only copy, leave it alone without flagging it for replacement; this project focuses on organizing the existing collection, not growing or upgrading it.
- Reopen changed files and verify tags, images, and unchanged audio before reporting success.
- Keep a verified embedded front cover and one `Folder.jpg` when the folder represents a single album and a single appropriate cover. Report unresolved artwork explicitly.

Not carried forward as general rules:

- Artist-specific genre assignments, counts, quality choices, and historical file locations.
- Installing all dependencies temporarily and deleting helper code after each session. A maintained application needs a reproducible project environment.
- Blanket deletion of legacy images. Image cleanup is a separate, previewed operation after verification.
- Assuming higher bitrate means better sound, especially across MP3 and WMA codecs.

The old file references `NO_ALBUM_ART.md`, but it is not present in this workspace. Do not invent its contents. The new application should retain explicit artwork exceptions with a reason and an option to retry when new evidence becomes available.

## 3. Filenames and folder names

### Naming templates: confirmed rules

| Available information | Filename |
| --- | --- |
| Artist, album, track, title | `Artist - Album - NN - Title.mp3` |
| Artist, album, title; track unknown | `Artist - Album - Title.mp3` |
| Artist and title; album unknown | `Artist - Title.mp3` |

Use `.wma` for WMA files; never change the extension to pretend to convert audio. Track numbers use at least two digits in filenames, such as `01`; metadata stores numeric track and total values, commonly displayed as `1/10`.

The UI must let the user retain a WMA file or request a real conversion to a new audio file. Conversion changes encoded audio and is separate from tag editing or renaming; the file extension must reflect the newly encoded format.

`Artist` in every filename template means the complete track-artist credit. For example: `Dr. Dre feat. Snoop Dogg - Album - 01 - Song Title.mp3`.

The user confirmed this filename pattern on 2026-09-04. Unknown artist/title values should remain unresolved; keep the current filename until a safe name can be proposed.

For multiple discs, use `Artist - Album - D02-03 - Title.mp3`, meaning disc 2, track 3. The user confirmed this convention on 2026-09-04.

Confirmed folder layout: `Root\Album Artist\Album\filename`. For a compilation, the album artist is normally `Various Artists`, so it is placed under `Root\Various Artists\Album`. When no album is known, place the file under `Root\Album Artist\Singles & Rarities`. Separate releases with the same album title need a release qualifier to prevent accidental merging.

### Windows constraints

Windows forbids `< > : " / \ | ? *`, NUL, and control characters 1–31 in ordinary filename components. Components must not end in a space or period. Reserved device names include `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, and `LPT1`–`LPT9`, including extension-bearing forms and the documented superscript-digit variants. Treat ordinary names as case-insensitive. Long-path support varies by application and configuration. [Microsoft filename rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file)

### Proposed deterministic translation policy

Apply this to individual filename/folder components, never to a whole path:

1. Preserve accents, non-English characters, spaces, apostrophes, and legal punctuation. Normalize generated names to Unicode NFC.
2. Translate `/` and `\` to `_`, retaining the old `AC/DC` → `AC_DC` convention.
3. Remove `:`, `?`, and `*`, retaining the old `*NSYNC` → `NSYNC` convention.
4. Translate double quotes to apostrophes; translate `<`, `>`, and `|` to `_`. Remove control characters.
5. Collapse repeated spaces; trim surrounding spaces and terminal periods.
6. Prefix a reserved device name with `_`; block empty names and `.`/`..`.
7. Validate the assembled destination, including its extension, root containment, existing files, and all other names in the same batch.

These replacement choices are application policy, not requirements imposed by Windows. The full original text remains in tags and the audit record.

| Tag text | Filename component |
| --- | --- |
| `AC/DC` | `AC_DC` |
| `*NSYNC` | `NSYNC` |
| `Who's Got the Herb?` | `Who's Got the Herb` |
| `Presents: Jock Jams` | `Presents Jock Jams` |
| `CON` | `_CON` |

Proposed conservative compatibility target: complete paths no longer than 240 characters, with a previewed shortening rule when needed. This is a project target, not the Windows maximum. Check actual component and path support during implementation; leave room for temporary names and qualifiers.

Collisions must be checked after translation and case normalization. Prefer an established version/release qualifier; when known duplicates still need distinct filenames, use stable numeric suffixes `(1)`, `(2)`, and so on. Never silently overwrite or repeatedly append suffixes on every scan. Treat an existing duplicate suffix as approved only when it is recorded or confirmed; `(2)` might be part of an actual title.

Compare filenames against tags using the same translation function. Legal punctuation loss is not a metadata mismatch. Running the naming operation twice must produce the same result.

## 4. Reading metadata, artwork, and music

The file contains both descriptive metadata and encoded audio. The music itself is not a metadata tag. Reading tags does not prove that the whole song decodes correctly or that its description is true.

### MP3 and WMA metadata

Proposed Python library: Mutagen. Its MP3/ID3 support exposes text frames and embedded `APIC` pictures. Its ASF support reads/writes the container normally used by WMA. Use full format-specific access when the simplified interface does not expose a field. [Mutagen formats](https://mutagen.readthedocs.io/en/latest/), [ID3 handling](https://mutagen.readthedocs.io/en/latest/user/id3.html), [ASF handling](https://mutagen.readthedocs.io/en/latest/api/asf.html)

| Attribute | MP3 ID3 field | Typical WMA/ASF field |
| --- | --- | --- |
| Title | `TIT2` | `Title` |
| Track artist | `TPE1` | `Author` |
| Album artist | `TPE2` | `WM/AlbumArtist` |
| Album | `TALB` | `WM/AlbumTitle` |
| Track | `TRCK` | `WM/TrackNumber` |
| Disc | `TPOS` | `WM/PartOfSet` |
| Date/year | `TDRC` in ID3v2.4; version-dependent otherwise | `WM/Year` |
| Genre | `TCON` | `WM/Genre` |
| Embedded image | `APIC` | `WM/Picture` |

These are the initial adapter mappings to validate on sample files, including legacy WMA track fields and differing value types. WMA artwork needs parsing/serialization of its structured picture value; it is not simply an ID3 frame or bare JPEG field. The old workflow used `WM/Picture`; confirm round-trip behavior before enabling WMA writes.

Proposed metadata behavior:

- Store normalized fields for the UI alongside the original format-specific values.
- Retain original values only in the temporary batch record so a reviewed tag-clearing operation can be recovered before temporary backups expire.
- Preserve existing tags, comments, lyrics, ratings, ReplayGain values, custom fields, and additional images unless reliable evidence establishes that they are wrong or the reviewed update specifically includes them.
- Distinguish the selected release date from original release date. Do not silently assign a compilation's date to the original recording or vice versa.
- Preserve legitimate producer credits; remove title text only when established as extraneous.
- Correct genre when reliable corrected metadata is available. Otherwise preserve a meaningful existing genre; do not impose one artist's genre rule globally.
- Compatibility targets are Windows Media Player, VLC on the user's phone, and MP3 playback from the wife's Kinobo A12 headphones through a TF (microSD) card. Start with conservative MP3 tagging and artwork choices, then validate representative files on each target before enabling bulk changes. Choose ID3v2.3 versus ID3v2.4 after establishing the Windows Media Player version and testing compatibility. Do not accept a library's implicit version conversion without reviewing field loss. Mutagen's ID3 defaults and conversions require explicit handling. [Mutagen ID3 version behavior](https://mutagen.readthedocs.io/en/latest/user/id3.html)

### Audio inspection and playback

Scan selected files for audio quality: codec, duration, sample rate, channels, bitrate, container/stream information, and full decode errors. Use `ffprobe` for technical properties and an FFmpeg decode check for full-stream errors; probing a header alone is insufficient. Decoding for analysis does not require saving or replacing the source recording. [ffprobe documentation](https://ffmpeg.org/ffprobe.html), [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html)

WMA conversion is a confirmed UI feature. The conversion screen must show source and target codec settings, expected destination name/path, and a clear choice to retain or remove the original WMA after successful verification. It must not be folded into an ordinary metadata-change batch. Verify the converted output by decoding it and checking its tags/artwork before reporting success. Removal is never automatic: it requires the user to select it in the reviewed conversion plan.

Lossy-to-lossy conversion cannot preserve or recover the source's original quality. WMA and MP3 bitrate values are not directly equivalent: for example, encoding a 128 kbps WMA as a 320 kbps MP3 creates a larger file but cannot restore audio detail that the WMA encoding removed. The user chose a source-matched conversion policy: target the WMA's measured bitrate in the MP3 output when it is a valid MP3 bitrate, otherwise use the closest supported MP3 bitrate and show that mapping in the review. The UI must describe this as a compatibility/size choice, not a quality upgrade.

Include in-app playback with play, pause, and seeking so the user can listen while reviewing tags, artwork, identity candidates, and duplicates. Qt's `QMediaPlayer` is a candidate, but test MP3 and the actual WMA variants on the target PC. Unsupported or protected files must be reported and left unchanged. [Qt playback documentation](https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaPlayer.html)

Keep three different checks separate:

- Whole-file SHA-256: detects any byte change and identifies byte-identical files.
- Audio-payload hash: checks encoded audio independently of tags. Implement format-aware extraction; WMA requires ASF-aware handling. Do not label a whole-file hash as an audio hash.
- Acoustic fingerprint: suggests the same recording across different encodes; it is not proof of identical bytes, sound quality, or exact release edition.

Tag-only edits must preserve encoded audio. Validate payload preservation on fixtures before enabling production writes. If reliable payload extraction is unavailable for a supported variant, keep writing disabled for that variant until an adequate preservation check exists.

## 5. Online identification and artwork sources

Use APIs where available, with clickable source pages for manual review. Do not build the first version around brittle website scraping.

| Source | Purpose | Access and limitations |
| --- | --- | --- |
| [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_API) | Artist, recording, release, track list, disc/track positions, dates, identifiers | Public catalog lookup; identify the application with a User-Agent and throttle to no more than one request per second. Community data can contain gaps or mistakes. |
| [AcoustID / Chromaprint](https://acoustid.org/webservice) | Generate a local audio fingerprint and look up candidate recordings/MusicBrainz IDs | Application key required. Free service is for noncommercial use; limit three requests per second. Send fingerprint and duration, not the entire music file. A lookup miss means unidentified, not incorrect. |
| [Cover Art Archive](https://musicbrainz.org/doc/Cover_Art_Archive/API) | Retrieve artwork associated with MusicBrainz releases | Prefer a front image for the selected release. An available image does not independently verify the audio. Handle missing art and redirects. |
| [Discogs](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use) | Secondary release/edition and packaging research | Useful manual fallback. API integration is optional and requires checking current authentication, image use, and service terms. |
| Official artist/label release pages and liner notes | Resolve edition, credit, and version disagreements | Manual evidence; usually no common API. Record the exact source used. |
| [ACRCloud](https://docs.acrcloud.com/reference/identification-api/identification-api) / [AudD](https://docs.audd.io/) | Optional additional recognition for unresolved audio | Account-based services; check current plans before enabling. Depending on integration, requests send audio samples or provider-specific fingerprints. Not part of the default initial scope. |

Confirmed first-version integration: free services only—MusicBrainz + AcoustID + Cover Art Archive. Cache results, use bounded retries/backoff, and honor provider limits across all workers. Store keys outside the repository and omit them from logs. No automatic submissions to public music databases are required. Paid recognition services may be considered later if unresolved files justify their cost.

### Matching workflow: proposed

1. Read current tags, filename, duration, and technical properties.
2. Find candidate catalog recordings using tags and filename clues.
3. Fingerprint the audio when identity is missing, disputed, or explicitly requested.
4. Compare candidates against artist, title, duration, version, and surrounding album tracks.
5. Select a release separately from selecting the recording. The same recording may appear on an original album, reissue, single, and compilation. Rank a valid current assignment first, then the original release; show those and other supported releases for the user to select. Do not change the release assignment without that selection.
6. Retrieve cover candidates for that release; show the evidence and proposed changes.

Track recording identity, release identity, and artwork confidence separately. Use understandable states such as unresolved, candidate, corroborated, and user-confirmed, with reasons. A provider score is not a calibrated probability. Neither duration alone nor a high fingerprint score proves clean/explicit status, a remaster, or the exact album edition.

For every lookup candidate, display the provider, its match score when supplied, and the evidence used, such as tag/filename agreement, duration, fingerprint result, release identifiers, and artwork association.

Save lookup results and evidence indefinitely in the local catalog, even when the user does not apply the proposed changes. Rejected proposals must not change the music file, but their result can remain available for later review until the user explicitly clears the catalog or removes the database.

If several releases fit, retain that ambiguity and let the user choose. An unidentified file is a supported outcome.

When no online match is available, allow the user to edit supported MP3/WMA tags manually and select a local JPG or PNG image file for embedded artwork. Show current and proposed tag/artwork values side by side before saving. Validate that image before embedding it. Allow an optional source URL and short note for a manually confirmed match; store them as current verification details in the application, not as music-file tags. Treat manual changes like all other changes: display them in the review, preserve unrelated metadata, verify the saved file, and keep an in-progress backup until the batch completes.

Selecting a file only displays its current catalog information. Online metadata, identity, and artwork lookup runs only when the user explicitly invokes a Lookup action; selection alone never starts a lookup. Lookup-generated proposals remain editable before application; retain the provider evidence while allowing the user to adjust proposed fields. Label any changed proposal `User edited`; do not require a reason before accepting the edit.

The Lookup action works for one selected file or multiple selected files. A multi-file lookup keeps candidates and proposed changes separate for each file and never applies changes automatically.

Provide a combined Lookup for metadata and artwork, plus separate Metadata Lookup and Artwork Lookup actions for cases where only one type of result is needed.

## 6. Artwork rules

- Match the selected release/edition; do not choose a cover solely because its album title looks right.
- When a verified cover for the selected release differs from existing embedded art, propose replacement and display the current and proposed front covers before the user selects it.
- Validate actual image decoding, format, dimensions, and byte size. A nonempty field may still contain an invalid or blank image.
- Embed one selected front cover while preserving other meaningful picture types by default.
- Keep one useful `Folder.jpg` where a folder represents one release and has one appropriate cover. Mixed folders, such as `Singles & Rarities`, must not acquire a misleading shared album cover.
- Do not replace an existing good image with a worse one simply because it came from an API.
- Artwork dimensions, byte-size limits, and JPEG/PNG compatibility depend on the target players and remain open decisions.
- When verified artwork cannot be found, offer a generic `Artwork not found` placeholder. Mark it as unresolved in the application database and, where supported, with a non-artwork marker in metadata so it cannot be mistaken for a verified cover. The placeholder may be embedded or used as `Folder.jpg` only when the user selects it in the reviewed plan. It must remain eligible for later replacement by verified artwork. Image deletion requires its own approved cleanup plan after the updated files have been verified.

Provide a user-managed exclusions list for specific files or folders. Each exclusion records its scope, reason, and the checks to skip, such as artwork lookup, online identification, fingerprinting, or duplicate analysis. Exclusions prevent repeated work but do not erase existing scan data; the user can review or remove an exclusion at any time.

Confirmed artwork policy: embed the selected cover in audio files and retain/create `Folder.jpg` for folders with a single appropriate album artwork.

## 7. Language and UI options

Confirmed UI choice: Windows desktop only. Both language options below can access `G:` through a process running on the Windows PC and call HTTPS APIs. Browser and remotely hosted interfaces are outside the project scope.

| Option | Fit | Tradeoff |
| --- | --- | --- |
| Python + PySide6 desktop UI | Recommended starting point: Mutagen, audio tools, and a single local desktop application | Package Python and media dependencies; validate playback and deployment on Windows. [Qt for Python](https://www.qt.io/development/qt-framework/python-bindings) |
| C# + WPF + TagLib# | Strong alternative for a Windows-focused application | Different metadata adapter; test field preservation and WMA behavior. [Microsoft desktop frameworks](https://learn.microsoft.com/en-us/dotnet/desktop/), [TagLib#](https://github.com/mono/taglib-sharp) |

Proposal: Python + PySide6, Mutagen, ffprobe/FFmpeg, Chromaprint, and SQLite. The Windows desktop platform and portable distribution are confirmed: package the application so it can run from a self-contained folder on the user's laptop and the wife's laptop, without a normal Windows installer. Keep the application executable/dependencies separate from the music library. AI is optional for explaining ambiguous evidence; ordinary parsing and rules should perform file modifications deterministically.

### Proposed application architecture

Use a layered desktop application so the first read-only prototype can grow into editing, conversion, duplicate review, and future SD-card export without replacing the UI:

- **PySide6 UI layer:** catalog, filters, selection, review/proposal editor, settings, progress/history, saved plans, and operation dialogs. Long-running work runs in worker threads or processes so the window remains responsive.
- **Application services:** scan orchestration, incremental catalog updates, lookup queue, review-plan management, change execution, verification, undo, and shared-library locking. Every write operation goes through one change executor.
- **Format adapters:** an MP3 adapter using Mutagen ID3 and a WMA adapter using Mutagen ASF. Adapters expose a common model while preserving format-specific and unknown fields.
- **Media tools:** bundled FFmpeg/ffprobe for technical inspection, conversion, and decode verification; optional Chromaprint/AcoustID fingerprinting only when requested or needed.
- **Provider adapters:** MusicBrainz, AcoustID, and Cover Art Archive clients with throttling, retries, credentials, evidence capture, and a provider-independent candidate model.
- **Persistence:** local SQLite for file records, scan snapshots, artwork state, lookup evidence, saved plans, queues, exclusions, operation history, and settings references. Store large artwork/cache files in the local workspace rather than SQLite.
- **Filesystem and Drive boundary:** a Windows filesystem service checks the configured `G:` root, availability, online-only access, locks, read-only attributes, path rules, and revalidation immediately before changes.

Keep all proposed changes immutable until the user selects them. The executor creates a pre-change catalog backup and temporary file backup, applies only selected operations, rereads and verifies each result, and records completed, skipped, failed, and undoable items separately.

### Proposed portable layout

Package the app with PyInstaller in a folder that contains the executable, bundled Python runtime, Qt libraries, FFmpeg/ffprobe, and Chromaprint binaries. Keep user data outside the application folder by default so replacing the portable app does not remove settings or catalogs. Use Windows Credential Manager for service credentials. The default local workspace is `C:\Users\<user>\.tempMp3Maint`; the library remains `G:\My Drive\Music` and is never used as the application install directory.

### Prototype sequence

1. **Read-only prototype:** validate the configured library, enumerate selected folders, download and read online-only MP3/WMA content on demand, populate SQLite, and display metadata, artwork, technical fields, issues, scan time, and progress/history.
2. **Review prototype:** add search, multi-selection, provider lookup, artwork preview, playback, editable proposals, and saved plans without writing files.
3. **Controlled changes:** add naming/folder planning, explicit selected-apply, backup, verification, undo, and error recovery.
4. **Conversion and duplicate workflows:** add WMA conversion and separate duplicate analysis/deletion after the core workflow is reliable.
5. **Future playlist/SD export:** implement after the Kinobo A12 ordering and card compatibility test.

The first implementation decision is therefore confirmed: build the read-only prototype with Python and PySide6, then package it as a portable Windows folder and test it on both laptops before enabling file-changing operations.

### Read-only prototype screens

The first prototype will contain four screens:

1. **Catalog:** library status indicator, folder/file selection, recursive-scan option, scan estimate, scan button, Issues only filter, search and field selector, grouped file table, and details pane.
2. **Scan activity:** current file path, download/read progress, cancel button, expandable directory history, retry/continue/cancel prompts, and a summary when changes or failures are found.
3. **File details:** current metadata, artwork preview, technical properties, last scan time, issue list, and playback controls. This screen is read-only in the first prototype.
4. **Settings:** library root, database path, temporary workspace, theme, search matching, retry count, credentials, and catalog-backup controls. Changes are validated before saving.

### Plan-centered editing workflow

Browsing and searching the catalog must work without a selected plan. The main window should show the active plan, or `No plan selected`, at all times. Opening a file, viewing details, playing audio, looking up metadata, and comparing candidates are allowed without a plan. Any action that creates or changes an edit proposal must require an active plan; if none is selected, explain that the user must create or select one first. The user may change the active plan at any time from the Saved Plans screen. Every metadata, artwork, rename, move, conversion, or other edit made through the UI is saved to the active plan immediately. Plan review shows all included proposals, allows edits and approval decisions, and Apply operates only on approved items from the selected plan.

The prototype will open on Catalog, remember folder and column selections per laptop, reset active filters and search text at startup, and keep the window responsive while scans run.

### Catalog selection and processing status

Add a checkbox as the first column of every catalog row and a status column immediately after it. Checkboxes, rather than ordinary row focus, control processing selection: one checked row shows its details pane; when two or more rows are checked, hide the details pane. A normal row click does not change the processing selection.
Include a master checkbox in the first-column header to select or clear all currently visible rows.
Provide one `Process selected` action. It determines the valid next action from each checked row's status, then opens a processing-status panel showing counts by action, queued/current/completed/error counts, the current file, and a Cancel button. Cancel stops after the current item and preserves completed work and catalog status.
When checked rows contain mixed statuses, process them in one operation and route each row according to its own status.
The `Scan` button is the only action that reads MP3/WMA content from the filesystem. A file read from disk is saved to SQLite but retains status `File`; a file loaded from SQLite retains status `DB`. Both `DB` and `File` rows are eligible for the next step, MusicBrainz lookup. `Process selected` must not reread `DB` rows. Use this action-group order for mixed selections: process eligible `DB` and `File` rows for MusicBrainz, retry `MB error` rows, then present `MB review` and `Plain` items for review.
Persist each row's processing status in SQLite across application restarts so queued, lookup, error, review, and plan work can resume.
If the app closes or loses connectivity while a row is `MB Lookup`, reset it to `MB Que` on the next launch so it can be retried.
When Drive is unavailable, allow MusicBrainz processing to use cached catalog metadata for selected rows; defer only actions that require reading or writing the filesystem.
Provide a manual `Reset status` action for checked rows. Offer only valid next-state choices for the current status, require confirmation, and record the reset in operation history.

Use these statuses and transitions:

- `DB`: the current file size and modified time match the catalog record, so the displayed data came from the database or an unchanged filesystem check.
- `File`: the file is new or its size or modified time changed; reread it from the filesystem and save the updated data to SQLite.
- `MB Que`: checked `File` rows are queued for MusicBrainz lookup.
- `MB Lookup`: a MusicBrainz request is currently running for that file.
- `MB error`: MusicBrainz returned an error after the configured maximum total attempts (default 3; configurable).
- `MB review`: MusicBrainz candidates returned and await per-file candidate review.
- `Plain`: file has a proposal saved in a plan and is ready for plan review and saving.

Process multi-file MusicBrainz work one file at a time. Show that file's candidates separately, preserve completed candidates in the local catalog when review is canceled, and allow review to resume later without repeating completed lookups. Checked `File` rows can be queued for MB; checked `MB error` rows can be retried; checked `MB review` rows open candidate selection followed by artwork lookup. Plan review edits and saves proposals to the active plan. Use one shared configurable maximum-attempt setting for temporary read and lookup errors, with 3 total attempts by default.

### Initial SQLite model

The first schema will use these tables, with schema migrations from the beginning:

- `library_roots`: configured root path and display name.
- `folders`: normalized path, parent folder, album artist/album classification, and scan state.
- `files`: path, filename, extension, size, modified time, content hash when available, scan time, availability state, and issue state.
- `metadata`: one current row per file for common fields plus serialized format-specific fields that must be preserved.
- `artwork`: embedded-image summaries, extracted cache paths, `Folder.jpg` state, hashes, dimensions, and verification state.
- `technical_media`: duration, codec, sample rate, channels, bitrate, and decode-check state.
- `scan_runs` and `scan_items`: operation status, timestamps, progress, errors, and retry outcomes.
- `lookup_requests` and `lookup_results`: queued requests, provider evidence, candidates, scores, and user decisions.
- `exclusions`: user-selected file/folder exclusions and skipped checks.
- `saved_plans` and `plan_items`: reviewed changes saved for later revalidation and application.
- `settings` and `catalog_backups`: per-laptop settings and rotating database-backup records.

Use stable internal IDs and normalized paths, but retain the original path and tag values for display and audit. Do not store audio bytes in SQLite; use the local workspace for temporary downloads, extracted artwork, and recovery backups.

### Prototype acceptance checks

The read-only prototype is ready for review when it can open the configured `G:\My Drive\Music` root, detect Drive availability, select one or more folders, enumerate recursively without following links, request online-only file content on demand, read MP3 and WMA metadata/artwork, populate SQLite incrementally, show the catalog grouped by album artist, display issues and last-scan times, and cancel safely while preserving completed scan results. It must not rename, move, delete, rewrite tags, convert files, or alter `G:` in this phase.

Programming-language decision gate: continue requirements interviews until the business rules and first-version screen workflow are stable. Decide the UI language and framework before implementing the read-only prototype, because the choice affects packaging, playback, MP3/WMA library support, and Windows integration. The current recommendation is Python + PySide6; C# + WPF remains the main Windows alternative.

### Settings screen

Include a Settings screen that lets the user choose light mode, dark mode, or follow the Windows theme; select the music-library root; select the local SQLite database location; select the temporary-workspace location for working copies and per-batch backups; choose case-insensitive or case-sensitive search matching; configure MusicBrainz and AcoustID credentials; set the automatic lookup retry count (default 2); and clear the local catalog. `Clear catalog` must offer clearing the entire catalog, selected folders, selected files, or selected data types such as lookup results, artwork cache, or duplicate-analysis data. Each option must show a preview of the data that will be removed and require explicit confirmation. Store credentials securely per laptop and never write them to project files or logs. Settings are independent on each laptop, while both installations can use the shared `G:\My Drive\Music` library. Defaults are `G:\My Drive\Music` for the library, `C:\Users\<user>\.tempMp3Maint` for the local workspace, and case-insensitive search.

Before saving settings, validate that the library root is readable, that database and workspace locations are writable, and that the workspace has adequate free space for the planned batch. Warn and require explicit acknowledgement if the database or workspace is inside the library root, because it could be scanned or synced accidentally. Changing a location must not move or delete existing files automatically; show the old and new path and let the user migrate or start fresh in a separate reviewed action.

Separate the UI, scan/index service, format adapters, online providers, match engine, filename rules, and change executor. This keeps metadata rules independent of screen code and allows provider replacements.

## 7.1 Future playlist and SD-card export

This is explicitly future work, not part of the first read-only or editing release:

- Build and save playlists for the user's media players.
- Allow the wife to select music and copy it to an SD card for her Bluetooth headphones.

The future exporter should copy MP3 files rather than modify the cloud library, create device-compatible playlist files where supported, estimate TF-card capacity before copying, and produce a transfer summary. It must preserve the source library and make duplicate/collision behavior visible. The first device profile will target Kinobo A12 headphones with TF-card playback. The available manual indicates that inserting a TF card and switching to TF mode starts playback automatically, with previous/next controls, but it does not document a selectable playlist or a guaranteed filename/metadata ordering rule. Treat playback order as unresolved until a small test card is used. Confirm its documented folder, filename, tag, artwork, playlist, and maximum-card-size limits; test an exported sample before treating it as supported.

Keep playlist data separate from library metadata: a playlist references library items and can later produce a portable copy. The user chose to store future playlists in the shared music library so both laptops can use them. A playlist editor must allow adding a complete album or individual songs. The future Kinobo A12 TF-card builder will use a selected playlist as its source, copy every selected playlist item directly into the TF card's root, and preserve the library filename for each song. It will not place an M3U8 playlist file on the card. If root-level filenames collide, show the collision and require a reviewed resolution before copying. Produce a transfer summary. Each laptop may cache playlist data locally for offline viewing, but the shared playlist file is the common source. The design should support at least M3U8 (Unicode M3U) as the starting interchange format for Windows Media Player and VLC, subject to testing.

## 8. Working safely with the mapped Google Drive

Google Drive for desktop can expose streamed files before their contents are available offline. Reading them can require downloading data. A successful local write does not itself confirm cloud synchronization. [Google streaming and mirroring guidance](https://support.google.com/drive/answer/13401938?hl=en)

Proposed application requirements:

- Design for the reported 60 GB across 18,844 files and 5,660 folders, with room for growth. Do not require mirroring the entire collection to use the application.
- Use ordinary local filesystem access through `G:` initially; no separate Google Drive API integration is needed for that design.
- Before starting a scan, check that Google Drive for desktop is running and the configured `G:` root is available and readable. Report unavailable files separately from corrupt files.
- When Google Drive is unavailable, permit viewing the local catalog and building a review plan from previously scanned data, but do not apply changes. Mark cached information with its scan time and wait until the required files and Drive are available before revalidating and applying the plan.
- Inventory names/sizes first; queue metadata reads, decoding, hashing, and fingerprinting separately. Show progress, cancellation, and retry/resume controls.
- Limit simultaneous reads so a large scan does not overwhelm streaming downloads.
- Keep each laptop's SQLite database, artwork cache, job state, and per-batch working copies in a local, per-user workspace outside the Google Drive library, proposed as `C:\Users\<user>\.tempMp3Maint`. The portable application's installation folder remains separate from this workspace. Do not create a temporary folder in the music library.
- Before writing, fully read the selected file, recheck it against the reviewed snapshot, and retain a verified original backup plus its original path in the dedicated temporary folder.
- Immediately before any file-changing operation—tagging, artwork, renaming, moving, conversion, or duplicate deletion—recheck Google Drive for desktop, the configured `G:` path, and the file's current availability.
- If a file-changing batch encounters an error, pause at that file and offer `Retry`, `Continue`, or `Cancel`. `Retry` attempts the same file again; `Continue` skips it and processes the remaining files; `Cancel` stops the pending work. Preserve completed work and report skipped, failed, and unprocessed files.
- Edit a working copy, verify it, then publish with a journaled per-file operation. Test replacement semantics on the actual mapped drive; do not assume a batch is atomic or that filesystem success means cloud sync completed.
- Recheck source/destination conflicts immediately before publishing. Skip externally changed files and return them for review.
- Resume interrupted batches from the journal; report completed, failed, and unprocessed files separately. Undo must not overwrite subsequent external changes.
- Provide an Undo button for the current reviewed batch while its temporary backup exists; let the user select individual files to restore. Default backup retention is 48 hours after verification and confirmed Drive sync, with an expiration warning.
- Before restoring an individual file, compare its current snapshot with the post-change snapshot. If it changed externally, skip restoration and warn rather than overwrite the newer version.
- Never follow directory links outside the selected root or include application backups in ordinary collection scans.

### Staged scanning for this cloud-only collection

1. **Selected-folder inventory:** choose one or many folders, then enumerate their paths, extensions, reported sizes, and modification times without intentionally opening audio contents. Count MP3, WMA, images, and other files separately. The first version inspects and changes only MP3 and WMA. Directory enumeration may still require network access and take time.
2. **Selected-folder inspection:** let the user select an artist, album, or other folder for tag and artwork inspection. Reading even just metadata may cause Drive to download/cache more data than the application requested; do not promise a download-free metadata scan.
3. **Audio checks on demand:** run decoding, payload hashing, and fingerprinting for selected files or batches. A complete integrity or duplicate audit can ultimately require reading the entire collection. Keep this separate from the initial inventory.
4. **Incremental follow-up:** persist the catalog in local SQLite on each laptop, including scanned paths, metadata, technical properties, artwork status, scan time, source IDs, and folder snapshots. On later runs, enumerate selected folders and use path, size, and modification time to identify new or changed files; reread metadata/content only where needed. These values are hints, not proof of unchanged content. Revalidate files before applying changes.

If a cataloged file no longer exists at its recorded path, mark it missing rather than deleting its catalog record. Provide a `Relink` action to locate the file at a new path, verify its identity, and update the catalog reference only after the user confirms.

Relink works for one missing file or multiple missing files. Show the proposed old-to-new path mapping and identity evidence for every file, then require confirmation before updating catalog references.

Relink can search a user-selected folder recursively for replacement files by default. Provide a checkbox to limit the search to direct files only. Display candidate mappings and identity evidence before updating any catalog references.

If Relink cannot find a confident replacement, leave the catalog entry marked missing and continue processing other candidates. Do not update a catalog reference from an uncertain match.

Start with one content-reading worker, with configurable concurrency after a small pilot. Use background work, a virtualized or paged file list, and lazy artwork thumbnails so the UI remains responsive. Save progress at file boundaries and support restarting after application closure or lost connectivity. Do not automatically start a whole-library inventory at launch or schedule background scans; scans run only when the user starts them.

The folder chooser must allow selecting one or many folders. Scans include selected folders and all subfolders by default; provide a checkbox to limit the scan to files directly inside the selected folders. It must also offer an alphabet/number selector that selects all first-level album-artist folders whose first significant character matches the chosen letters or digits, for example `A`, `B`, `C`, or `0`–`9`. The UI should show the exact matched folders and file count before scanning. Symbols and non-Latin names remain individually selectable and must not be silently omitted by the alphabet/number selector.

Show queued, inspecting, inspected, unavailable, and failed states separately. Display bytes read by the application when measurable; do not label that as exact Google Drive network traffic. The app should manage its own cache budget without deleting or manipulating Drive's internal cache.

An offline session may show previously indexed information, clearly marked with its scan time; it cannot assume the corresponding audio is locally available. It may build a pending review plan, but cannot apply it until Drive is available and the files are revalidated. No automatic whole-library content scan should start on application launch.

Applying selected changes still requires downloading the affected originals, creating local backups and working copies, verifying the result, and writing it back through `G:`. Local working space is therefore required even though the source collection lives in the cloud. Check space for each planned batch and retained backups; do not require 60 GB of local space by default.

Confirmed backup approach: create temporary working copies and per-batch backups in a local per-user workspace such as `C:\Users\<user>\.tempMp3Maint`. This keeps temporary data out of the synced Google Drive library and gives each laptop an independent workspace. The user maintains the original MP3 library on a separate backup hard drive as the long-term recovery copy. Retain temporary backups for 48 hours after the application verifies the changed files and observes Google Drive synchronization for the batch, then delete them. Provide an Undo button for the current reviewed batch while its backup exists, show its expiration time, and warn before deletion. If synchronization cannot be confirmed, retain the batch files and mark the batch incomplete rather than deleting them. Do not retain a searchable history after that temporary recovery window. Make the retention period configurable later.

The portable application may be installed or copied separately onto each laptop, and both instances have the same full scan, cleanup, conversion, and duplicate-deletion controls. Read-only scanning is allowed concurrently. Each laptop retains its own local catalog database, so neither needs a full rescan at every application launch. Before editing, acquire a shared library-edit lock, revalidate every reviewed file, and refuse or defer a conflicting batch. This prevents simultaneous modifications while allowing each laptop to maintain its own local index and temporary workspace.

## 9. Proposed first UI and implementation stages

Main flow: select folder → scan → review issues → inspect candidate tags/artwork and listen → select changes → preview destinations → apply → inspect verification results.

The file list should group files by album artist, matching the top-level folder organization. Within each group, sort by album and then track number by default. Allow an alternate sort by clicking visible column headers, including artist, title, filename, duration, bitrate, last scan time, or other displayed fields. Show all available scanned files by default except missing files; missing files appear when `Issues only` is enabled and remain in the catalog for Relink. Show format, artist, title, album, track/disc, duration, artwork state, identity state, last scan time, and issues. Include an `Issues only` checkbox to narrow the list to files needing attention, plus a search box and field selector for artist, album, title, and filename. The field selector defaults to `All`. Searches are exact by default and allow `*` wildcards at the beginning, end, or middle of the search string; for example, `*mix*`, `Artist*`, or `Album*Deluxe*`. Reset active filters and search text when the application opens. Keep a separate per-laptop history of the last 10 search entries, selectable from a dropdown or replaceable by newly typed text, with a clear-history option. A details pane should show before/after values, evidence links, playback, and reasons for uncertainty. Filters should include missing tags, missing art, mismatches, unreadable files, and possible duplicates.

Support multi-file selection with reviewed batch actions. Allowed actions are: apply common album artist, album title, year, genre, or artwork; assign a selected MusicBrainz release and map individual titles/track numbers from it; rename/organize each selected file from its own reviewed tags; clear one known-wrong field; and convert selected WMA files. Let the user independently select tag updates, artwork updates, filename changes, and folder moves in the same batch, including a rename-only batch. Disable an action when the selection cannot safely support it, such as applying one album cover to mixed-album files. Never copy one title, track number, or track-artist credit blindly to every selected file. Show the before/after value, destination path, and validation result for every file before applying the batch.

Persist the current scan data, selected matches, user overrides, artwork exceptions, and proposed destinations needed by the active application workspace. Keep duplicates and quality findings distinct from tagging errors. Do not provide a searchable per-file change-history feature; retain only the temporary batch record needed for in-progress recovery and verification.

### Dedicated duplicate-cleanup workflow

Duplicate discovery and cleanup are separate from ordinary scan, tag, artwork, rename, and conversion batches. The user selects folders for this process. The application must identify byte-identical files separately from likely duplicate recordings with different encodes or tags, display evidence such as audio hashes, fingerprints, duration, codec, bitrate, sample rate, decode errors, and artwork, and preserve meaningful alternate versions. Quality results must be available in the duplicate comparison so the user can use them to decide which copy to retain. It may add stable `(1)`, `(2)`, and later suffixes to known duplicate filenames where needed to keep each file distinct.

The user chooses which copies to retain or delete. Before deletion, show the exact original paths, selected retention copy, reasons/evidence, and an explicit delete preview. Require a separate final confirmation for the duplicate-deletion batch after that preview. Perform deletion through the mapped `G:` drive, using the selected owned library content; do not add a separate Google-account ownership filter. Verify that Google Drive for desktop syncs the removal to Google Drive's Trash before reporting completion. If the expected cloud-trash result cannot be confirmed, show a clear warning and leave the file unchanged where possible. Validate this behavior with a test duplicate before enabling production duplicate cleanup. Google Drive normally retains trashed items for 30 days, after which they are permanently deleted. [Google Drive Trash retention](https://support.google.com/drive/answer/14933051?hl=en) Do not delete solely because a file has a similar title or a lower bitrate. Archive folders are outside this application's duplicate-cleanup scope.

1. **Design decisions:** Windows desktop, selected-change review, and cloud-only collection scale are confirmed. Settle naming, playback compatibility, lookup budget, and local working/backup storage next.
2. **Read-only prototype:** select a folder; inventory MP3/WMA; display tags, artwork, and technical properties in the application. No renames, writes, or report export.
3. **Lookup/review:** cached catalog search, fingerprints, release selection, artwork previews, and playback.
4. **Controlled editing:** backups, explicit batch preview, tag/artwork edits, renames, folder organization, validation, and recovery.
5. **WMA conversion:** a user-selected UI operation that creates and verifies a new audio file; the user may select removal of the original WMA after verification, and encoding presets are established before implementation.
6. **Later additions:** image cleanup and optional recognition providers. Replacing low-quality unique files is outside the project scope.

Folder organization is optional for every reviewed batch. The user may correct tags and artwork while leaving the existing folder location unchanged, or may select the separately previewed move into `Album Artist\Album` or `Album Artist\Singles & Rarities`.

Before production writes, test on copies: illegal/reserved names; case and normalization collisions; long paths; multiple discs; missing tags; differing ID3 versions; MP3 and WMA artwork; unknown-field preservation; interrupted operations; external changes; unavailable Drive files; and unchanged encoded audio. Repeated scans must not propose changes to already compliant files.

## 10. Interview and open decisions

### Decisions confirmed on 2026-09-04

- Windows desktop application only.
- Playback targets: Windows Media Player 11.2607.16.0 on this PC, VLC on the user's phone, and wife's Kinobo A12 Bluetooth headphones using a TF (microSD) card.
- Review proposed changes, then apply selected changes.
- Google Drive files are cloud-only and accessible online through `G:`.
- User reports approximately 60 GB, 18,844 files, and 5,660 folders; no program inventory has verified the format breakdown.
- Use `Artist - Album - NN - Title.ext`, omitting album or track number only when it is unknown. Preserve `.mp3` or `.wma` as appropriate.
- Include the complete track-artist credit, including featured artists, in filenames; continue to use album artist for folder organization.
- When a recording has multiple supported releases, present the current valid assignment first, then the original release, and require the user's selection before changing it.
- The UI must let the user keep WMA files or request a real conversion to a new audio format; conversion is separate from metadata edits.
- After a successful WMA conversion and verification, the reviewed conversion plan may remove the original WMA when the user selects that action.
- WMA-to-MP3 conversion targets the source WMA's bitrate when possible, otherwise the closest supported MP3 bitrate; the UI shows the mapping before approval.
- Use a local per-user workspace such as `C:\Users\<user>\.tempMp3Maint` for temporary working copies and per-batch backups. Delete a batch's temporary files only after verification and confirmed Drive sync; the external backup hard drive is the long-term original-library backup.
- Distribute the app as a portable Windows application for this laptop and the wife's laptop. Each instance must prevent conflicting edits to the shared cloud library.
- Give both laptops the same full application controls; do not create a restricted mode for the wife's laptop.
- Keep Settings independent on each laptop while allowing both installations to use the shared music-library root.
- Store future playlists in the shared music library so both laptops can use them; local caches are secondary.
- Allow a playlist to receive an entire album or individual songs, and build the future Kinobo A12 TF card from a selected playlist.
- Copy playlist songs directly to the TF-card root while preserving library filenames; require review for root-level collisions.
- Do not copy an M3U8 playlist file to the Kinobo A12 TF card; copy only the selected MP3 files.
- Before copying, compare the total selected-file size with available TF-card space and stop with a clear explanation if it will not fit.
- At the start of an SD-card build, ask whether to clear existing files from the TF card. Clearing affects only the selected removable card, requires explicit confirmation, and must complete before copying begins. If the user keeps existing files, handle each filename collision individually as it is encountered, offering a reviewed choice such as skip, replace, or choose a different export name.
- Detect the destination drive type and enable clear-card only when Windows identifies it as a removable TF/SD card. Do not permit clear-card on an ordinary folder or fixed drive.
- Immediately before clearing or copying, recheck that the same removable card is connected, writable, and has enough free space for the selected files.
- Warn when the TF card's filesystem, capacity, or other detected properties may be incompatible with the Kinobo A12. Never format the card automatically; any formatting remains a separate user action outside this application.
- Before transfer begins, show a final file list containing each source path, preserved destination filename, collision decision, and total size. Require the user to approve that transfer list.
- Show live transfer progress and allow safe cancellation. A canceled transfer leaves files already copied in place and clearly identifies completed and incomplete items.
- Provide a scan Cancel button that stops after the current file, preserves completed catalog results, and marks the scan incomplete.
- After copying finishes, offer a `Verify transfer` checkbox in the final transfer options. When selected, compare each destination file's size and checksum with its source and report the results. Allow `Cancel verification` to bypass the remaining checks; keep the copied files and mark verification as skipped rather than failed.
- Select `Verify transfer` by default for new transfers; the user may clear it before copying or cancel verification after copying begins.
- Because Kinobo A12 playback order is undocumented, test whether it follows copy order, filename order, or another device scan order before promising playlist order. Preserve library filenames while testing; any ordering workaround must be shown as an export-only choice.
- Before implementing Kinobo A12 ordering, perform a small test-card trial with deliberately ordered sample filenames, record startup and next/previous behavior, and use the observed result to define the device export profile.
- Keep a local SQLite catalog database on each laptop so later scans compare selected-folder snapshots and rescan only new or changed files; allow offline review planning but wait for Drive availability and revalidation before applying changes.
- Include in-app playback with play, pause, and seeking for review of MP3/WMA files and duplicate candidates.
- Run scans only when the user starts them; do not run scheduled or automatic background scans.
- Check Google Drive for desktop and the configured library path before scanning; if unavailable, keep the existing catalog available and explain why the scan cannot start.
- Recheck Drive and `G:` immediately before every approved change, move, conversion, or deletion; defer the operation if unavailable.
- Pause a batch on its first error and provide Retry, Continue, and Cancel choices; preserve completed work.
- Include a Settings screen for light/dark/follow-Windows theme; music-library root; local database location; and temporary-workspace location, with path validation and a warning for database/workspace paths inside the library.
- Show all scanned files by default and provide an `Issues only` checkbox.
- Group the review list by album artist.
- Provide a search box for artist, album, title, and filename across scanned files.
- Reset active filters/search text at startup while retaining a clearable per-laptop dropdown of the last 10 searches.
- Use exact search matching by default, with `*` permitted at the beginning, end, or middle of a search string.
- Search is case-insensitive by default; provide a Settings option for case-sensitive matching.
- Provide an Artist/Album/Title/Filename field selector with `All` as the default.
- Store the selected field with each search-history entry and restore it when that entry is selected.
- Keep the scan engine separate from the activity-panel presentation so the prototype can change between tree, two-panel, or summary layouts without rewriting scan logic.
- Sort within album-artist groups by album and track number by default; allow alternate sorting by visible column headers.
- Remember column visibility, order, and sorting preferences independently on each laptop.
- Display each file's last scan date/time in the catalog and allow sorting by that column.
- Include hidden and system files under selected folders by default; provide a scan/settings option to exclude them when needed.
- Do not follow Windows shortcuts, symbolic links, or junctions; scan only files physically contained under the selected folders.
- If a selected file is read-only, attempt to clear its Windows read-only attribute automatically before writing; if writing still fails, use the configured Retry/Continue/Cancel handling and record the issue.
- Normalize organized file extensions to lowercase `.mp3` and `.wma`.
- If the proposed path exceeds the configured Windows-safe limit, shorten folder and filename components automatically while preserving required artist, album, track, and title information as far as possible; show the resulting name in the review before applying it. Record any shortened component as an issue.
- Preserve valid Unicode characters, including accented letters and non-Latin scripts; translate only characters Windows forbids in paths.
- Write updated MP3 tags as ID3v2.3 with UTF-16 by default for Windows Media Player and hardware compatibility. Provide a setting to use ID3v2.4 with UTF-8 for users who prefer the newer format.
- Preserve artwork source resolution when practical, but automatically downscale oversized images for player compatibility and manageable file sizes; show the resulting image in review before applying it.
- Convert artwork to JPEG when possible for embedded covers and `Folder.jpg`; retain the source image only when conversion is not practical, and show the output format in review.
- Do not directly integrate with or refresh Windows Media Player; the player remains responsible for detecting library changes.
- If another program has a file locked, pause the active operation and offer `Retry`, `Skip`, or `Cancel`; record skipped or failed files as issues.
- Preserve the original Windows modified timestamp for metadata-only edits when possible. File moves, renames, conversions, and other content changes use the normal resulting filesystem timestamp.
- After applying metadata, artwork, rename, move, or conversion changes, automatically reread and verify every changed file against the approved result; report any mismatch and retain recovery data according to the backup-retention rule.
- Allow files and folders to be added to a scan or review selection by dragging them from Windows Explorer into the application.
- Show core metadata fields in the manual editor by default—artist, album artist, album, title, track/disc numbers, year/date, genre, composer, and artwork—with an expandable `All fields` view for other readable tags.
- Allow a reviewed change plan to be saved for later application when Google Drive is unavailable; revalidate every file and require the normal review/confirmation checks before applying the saved plan.
- Keep saved review plans indefinitely until the user applies or explicitly deletes them; show plans that reference missing or changed files as requiring revalidation.
- Keep saved review plans local to the laptop that created them; do not place plan files in the shared music library.
- Show an always-visible Google Drive/library availability indicator in the main window, with enough status detail to distinguish available, offline, and unavailable or revalidating states.
- When Google Drive is unavailable, periodically check for its return while a pending operation is waiting; make the polling interval configurable, with 30 seconds as the initial default, and allow the user to stop waiting.
- When the Drive returns, keep the pending operation paused and prompt the user to Continue after the app rechecks the relevant files; do not resume changes automatically.
- If an online metadata or artwork lookup is requested without internet access, save it in a local lookup queue and offer to run it when connectivity returns; do not apply any queued result without the normal review and confirmation.
- Keep queued lookup requests indefinitely until completed or explicitly deleted; show requests whose files changed or disappeared as requiring revalidation.
- Allow the application window to be minimized while scans, lookups, edits, conversions, or transfers continue; show current progress when the window is restored.
- When a minimized operation finishes, show a Windows notification with the operation result and provide an action to reopen the relevant results view.
- Open the application to the catalog for the configured music-library root. Reset active filters and search text at startup while retaining the separate search-history dropdown.
- In Google Drive for desktop `Stream files` mode, request/download online-only MP3/WMA content as needed for scanning, lookup, validation, conversion, or editing. Process downloads incrementally rather than pre-downloading the library, show download/read progress, honor Drive availability and bandwidth limits, and rely on Drive's managed local cache instead of creating a second permanent library copy. Folder enumeration may list paths before file content is downloaded.
- Do not manage or purge Google Drive's streaming cache. If Drive reports insufficient space or cannot provide a file, allow its normal handling to continue; record the file as an issue if the read or operation ultimately fails and use the configured Retry/Continue/Cancel flow where applicable.
- The normal scan reads metadata and embedded artwork for every MP3/WMA. Run AcoustID fingerprints and full audio-decode/quality checks only when an issue, lookup, duplicate analysis, conversion, or explicit user request requires them.
- The Catalog table places `Album artist` in the first column, followed by artist, album, track/disc, title, format, duration, artwork state, and last scan time.
- Before a scan that may download online-only files, estimate the likely download size and duration from available file sizes and show the estimate with `Continue` and `Cancel` choices. Treat the estimate as approximate and update progress with actual results.
- Create rotating automatic backups of each laptop's local SQLite catalog database. Store them in the configured local workspace or database-backup location, retain a configurable number of recent copies (7 by default), and provide restore and delete actions with confirmation.
- Create an additional catalog backup immediately before every file-changing batch; do not begin the batch if that backup cannot be completed and recorded.
- Leave the local SQLite catalog database unencrypted. Store online-service credentials separately and securely through Windows credential storage; never place credentials in the catalog or logs.
- Require the application to close and restart after restoring a catalog backup so every view and database connection reloads cleanly.
- When the configured music-library location changes, preserve the existing catalog and create or select a separate catalog for the new root; do not clear prior catalog data automatically.
- When the temporary-workspace location changes, leave existing backups and recovery files where they are and use the new location for future operations; show the old location so the user can clean it up manually.
- When the database location changes, leave the existing database untouched and initialize or select a new database at the chosen location; do not move or delete the prior database automatically.
- When a manually started scan finds no new or changed files, display the existing catalog without an extra confirmation message.
- When a scan finds added, changed, unavailable, or failed files, show a scan summary with counts and affected paths. A scan with no changes continues to show the existing catalog quietly.
- Keep the scan summary visible until the user closes it; do not auto-dismiss it.
- Provide actions in the scan summary to open affected files or folders directly in the review list.
- During a scan, show one current file path in the main progress area. Provide a `History` button that opens a larger activity panel listing directories and files processed during the current scan. Keep this activity available until the scan summary is closed, while storing only the catalog data and temporary recovery records defined elsewhere.
- Initial activity-panel layout: an expandable directory tree, with directories collapsed by default and their files shown when expanded. Treat this as a prototype choice that can be revised after hands-on use.
- First-version UI choice: use the expandable directory-tree activity layout as a fixed layout for everyone. Reconsider alternatives after prototype use.
- Show a short help description the first time each major screen opens, with a way to view the help again later.
- Keep first-use help general and reusable; do not include personal library paths or user-specific examples.
- Support multi-file selection with reviewed batch updates for compatible album fields, artwork, release mapping, organization, tag clearing, and WMA conversion; preview each file's exact result before applying.
- Make album-folder organization optional per reviewed batch; tag and artwork changes may be applied without moving files.
- Let the user independently select tag changes, artwork changes, filename changes, and folder moves in a reviewed batch, including rename-only changes.
- Embed selected album artwork in the audio files and retain/create `Folder.jpg` only for folders with a single appropriate cover.
- Propose replacement of existing embedded artwork when research finds a different verified cover for the selected release; apply it only after user review.
- Offer a clearly labeled generic placeholder when verified artwork cannot be found; track it as unresolved and allow later replacement.
- Keep a user-managed exclusion list for files/folders and selected repeated checks, with a reason and the ability to remove it later.
- Start scans from one or many selected folders. Remember the last selected folders separately on each laptop, but require the user to start each scan manually. Provide an alphabet/number selector for all first-level album-artist folders beginning with chosen letters or digits, and preview the matched folders before scanning.
- Scan selected folders recursively by default; provide a checkbox to scan only files directly inside selected folders.
- Allow safe scan cancellation after the current file, preserving completed results and showing the scan as incomplete.
- If a scan cannot read a file, pause and offer `Retry`, `Continue`, or `Cancel`. Preserve catalog entries already collected and report unreadable, skipped, and unprocessed files.
- When the user chooses Continue for an unreadable file, mark it unresolved and eligible for retry during a later scan.
- Provide a `Retry unreadable files` action that scans only files that previously failed to read. Keep metadata-identity uncertainty and missing artwork as separate states that this action does not retry.
- A canceled scan starts over when run again; previously collected catalog data remains available, but the scan does not resume from its stopping point.
- Keep scan and audit results in the application; do not add Excel/CSV/PDF report export.
- Clear a tag value when it is known to be wrong and no correct replacement is established; include the cleared value in the user-reviewed change preview.
- Correct genre when reliable metadata establishes a value; otherwise preserve the existing meaningful genre.
- Preserve all other existing metadata unless it is known to be wrong or included in the reviewed update.
- Provide manual tag editing and local-artwork selection for MP3/WMA files when no online match is available; review and verify the manual update before applying it.
- Show current and proposed values side by side in the manual editor before saving.
- Do not start online lookup merely from file selection; require an explicit user-invoked Lookup action.
- Allow explicit Lookup for one file or multiple selected files, with separate candidates and proposed results per file.
- Offer combined metadata/artwork Lookup and separate Metadata Lookup and Artwork Lookup actions.
- Show provider, match score, and supporting evidence for every lookup candidate before selection.
- Allow lookup-generated proposals to be edited before application while retaining their provider evidence.
- Label a modified lookup proposal `User edited`.
- Do not require a reason when a user edits a lookup proposal.
- Save lookup candidates and evidence locally even when proposed changes are rejected; do not modify the music file unless changes are selected and applied.
- Retain saved lookup results indefinitely until the user explicitly clears the catalog or removes its database.
- Provide a Settings `Clear catalog` action that previews the catalog data to be removed and requires confirmation.
- Offer full-catalog, selected-folder, selected-file, and data-type catalog clearing options, each with a removal preview and confirmation.
- Provide MusicBrainz and AcoustID credential settings with secure per-laptop storage; never log or store credentials in project files.
- Provide a `Test connection` action for each lookup service that reports credential, network, and service-limit errors without starting a music lookup.
- Allow MusicBrainz-only lookup when no AcoustID credential is configured. Use AcoustID fingerprinting when available, but do not block ordinary tag-based lookup if it is unavailable.
- In a multi-file lookup, pause on the first error and offer `Retry`, `Continue`, or `Cancel`, matching scan and edit behavior.
- Before showing those controls, automatically retry temporary lookup failures the configured number of times (default 2).
- Apply the same configurable automatic retry count to temporary scan and file-edit failures. Use 2 retries by default; allow 0 to disable automatic retries. Permanent errors pause immediately for Retry, Continue, or Cancel.
- Disable Clear catalog while a scan, lookup, file edit, conversion, or SD-card transfer is active.
- Prevent closing the application while a scan, lookup, file edit, conversion, or SD-card transfer is active. Re-enable closing after completion or safe cancellation.
- Accept local JPG and PNG images for manual artwork selection and validate them before embedding.
- Allow an optional source URL and short note for a manually confirmed match; store them as current application verification details rather than music-file tags.
- Provide a separate duplicate-cleanup process for selected folders. Label known duplicate filename collisions with stable `(1)`, `(2)`, and later suffixes; find and present duplicates for user-selected deletion without automatically deleting any audio.
- Scan selected files for technical audio quality and decode errors, and display those results in duplicate comparisons to help choose the retained copy.
- Duplicate cleanup offers retain or user-selected deletion only; it does not create archive folders.
- Delete user-selected duplicates through the mapped `G:` drive and verify that Google Drive for desktop sends them to Google Drive's Trash; do not permanently delete them.
- Require an extra final confirmation after the duplicate-deletion preview and before sending any files to Google Drive's Trash.
- Warn and leave the file unchanged if Google Drive Trash is unavailable or a requested trash operation cannot be confirmed.
- Leave a low-quality file alone when it is the only copy; do not propose replacement, deletion, upscaling, or other collection-growth work.
- For multi-disc releases, use `Artist - Album - DDD-TT - Title.ext`, such as `D02-03` for disc 2, track 3.
- Organize files as `Album Artist\Album`; use `Album Artist\Singles & Rarities` when album information is unknown. Compilation albums use their album artist, normally `Various Artists`.
- Use free lookup and recognition services in the first version. Reconsider paid services only after evaluating unresolved files.
- Artwork lookup uses a provider fallback chain. Cover Art Archive remains the preferred source for a selected MusicBrainz release. Add optional free sources such as the Apple iTunes Search API (album artwork URLs), with provider, URL, match evidence, and download errors shown during review. Discogs may be supported later when a user supplies an API token; Wikimedia Commons can be considered for manually confirmed images. No provider may replace artwork automatically.
- Every artwork proposal must offer `Keep current embedded artwork` when the file already contains artwork. This records an explicit keep action in the plan and leaves the embedded image unchanged when the plan is applied. Other choices are a reviewed online image, a reviewed local image, or the generic unresolved placeholder.
- Artwork review always displays a selectable status row for the online lookup, including `NOT FOUND` or download errors, and includes the current embedded image with a thumbnail and pixel dimensions when present. A failed online lookup therefore does not hide the keep-existing option.
- `Clear work` removes saved lookup candidates and removes selected files from saved plans, then resets those files to `DB`; it never deletes audio files or deletes the plans themselves.
- Support MP3 and WMA only in the first version; count but do not inspect or change other file types.
- Future enhancement: playlist creation and safe MP3 export to the wife's SD card, with no modification of the cloud-library source files.
- Initial plan application writes only approved text metadata after size/time revalidation and creates a timestamped local backup. Artwork replacement, filename translation, and file moves remain separate reviewed operations.
- Approved artwork choices are now embedded for MP3 files during plan application; the original is included in the backup and Undo restores it. WMA artwork writing remains a separate ASF-specific implementation.
- Replace the ambiguous `Plain` row status with `Plan - Pending`; after apply record `Plan - Complete`, `Plan - Partial`, `Plan - Error`, or `Plan - Skipped` per item and retain the overall plan result.
- Approved plan application now calculates Windows-safe destinations using the album-artist/album folder rules and the `Artist - Album - NN - Title.ext` pattern, preserves multi-disc numbering, adds collision suffixes, and records moves in the Undo manifest.
- MusicBrainz lookup requests extended release and relationship data and retains it as candidate evidence: release group, genres, labels, barcode, media/disc information, works, and MusicBrainz identifiers. The UI will expose these fields for review before any tag is changed.
- AcoustID is an optional fingerprint lookup. The app generates a Chromaprint fingerprint from the audio (normally through `fpcalc`), sends that fingerprint and duration to AcoustID, then uses returned MusicBrainz recording IDs to retrieve candidates. It requires a local Chromaprint/fpcalc installation and an AcoustID application key; ordinary tag-based MusicBrainz lookup remains available without it.

Interview approach: ask one question at a time and keep the remaining questions queued. An unanswered question is not acceptance of the proposed default.

Open design decision:

- SD-card playback ordering remains intentionally open until the Kinobo A12 test establishes whether the device follows copy order, filename order, or another scan order. After that test, choose the export ordering that produces the desired playback sequence.

Next unanswered question:

- Should the scan activity panel show only directories by default, with files expandable beneath each directory?

Queued follow-ups:

- Should the builder verify available TF-card capacity before copying?
- Should the builder verify that the selected destination is a removable TF/SD card before allowing a clear-card operation?
- Should the builder recheck the removable card and free space immediately before copying begins?
- Should the builder warn when the card's filesystem or capacity may be incompatible with the Kinobo A12, without formatting the card automatically?
- Should the app display a final list of files to be copied before the SD-card transfer starts?
- Should the SD-card transfer show live progress and allow you to cancel safely while copying?
- After copying, should the builder verify each destination file's size and checksum against the source before marking the transfer complete?
- If a file changed externally after the batch, should Undo skip that file and warn rather than overwrite the newer version?

Next questions, to ask in small groups:

- Library root confirmed as `G:\My Drive\Music`.
- How should compilations, featured artists, multiple discs, and unknown albums be organized?
- When the same recording appears on several releases, preserve the currently supported album assignment, prefer original releases, or choose manually?
- Keep WMA as WMA? The proposed default is preservation; any future conversion would be a separate feature retaining originals.
- Where can backups live, how much space is available, and how long should they remain?
- Is this for personal use only, and is a portable application or an installer preferred?

Record future answers here as dated decisions, updating the corresponding sections so this document remains the project's current design.
