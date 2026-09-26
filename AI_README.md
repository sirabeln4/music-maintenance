# Music Library AI Handoff

Last updated: 2026-08-24

## Purpose

This file records the user's preferred music-library cleanup workflow and the
work already completed. Read it before auditing or modifying another artist
folder so earlier discovery work is not repeated or accidentally undone.

Library root:

`G:\My Drive\Music`

The user normally asks to:

- Recursively inspect an artist folder and all subfolders.
- Validate MP3 filenames against embedded metadata.
- Correct artist, title, album, album artist, year, and track tags.
- Standardize filenames and organize confirmed album tracks into folders.
- Find and embed appropriate album artwork.
- Identify duplicates, alternate versions, bad assignments, and low-quality
  encodes.
- Recommend changes first when explicitly asked for recommendations.
- Apply the changes when the user says to update or approves the cleanup.
- When updating, always normalize the MP3 metadata before finalizing the file.
- When a verified album cover is available, always embed it in the MP3 files.
- Move songs into folders named for their album under the artist folder. Use a generic folder such as `Singles` or `Singles & Rarities` when no album applies.
- Remove redundant JPG artwork after validation, but retain one useful `Folder.jpg` per album folder where applicable.

## Working Rules

### Audit First

1. Inventory audio and image files recursively. Include MP3 and any other
   audio format the user mentions.
2. Confirm every audio file is readable before editing it.
3. Record duration, bitrate, sample rate, tags, artwork presence, and an audio
   payload hash that excludes metadata.
4. Compare filenames with the title and artist tags.
5. Use the filename and embedded audio tags together to determine the artist,
   song title, and album. Treat either source as a clue rather than assuming it
   is correct when the two disagree.
6. When an artist, title, or album is missing or the filename and tags mismatch,
   consult authoritative online sources such as MusicBrainz, official release
   listings, and the Cover Art Archive to validate the correct attributes.
   Apply an online correction only when the artist, song, version, and release
   match confidently; otherwise preserve the uncertainty and do not invent
   metadata.
7. Look for exact duplicates as well as likely alternate encodes with similar
   titles and durations.
8. Verify official releases against MusicBrainz or another authoritative
   catalog. Use Cover Art Archive for verified front covers.
9. Do not infer that two similarly named files are duplicates when their
   durations or audio fingerprints differ.

### Metadata Conventions

- Use canonical artist casing, such as `50 Cent`, `3 Doors Down`, `2Pac`, and
  `Three Dog Night`.
- Preserve featured-artist credits in the artist tag. Keep the album artist
  set to the primary album artist.
- Use the official album title and release year.
- Use track values in `number/total` form when the release is established.
- MP3 track tags use the release's actual numeric value (for example '1/10', not necessarily '01/10'). Filenames zero-pad numbers below 10 (for example '01') for consistent sorting.
- Remove bogus track values such as `50`, placeholder values, and incorrect
  copied track numbers.
- Remove producer credits and download-site text from song titles. Producer
  information may remain in dedicated credits if already available.
- Correct punctuation, apostrophes, spelling, capitalization, underscores,
  doubled extensions, and trailing spaces.
- Use `Hip-Hop` for normalized 50 Cent genre tags. Follow the established genre
  when working with other artists.

### Filename Conventions

Use the embedded track artist, album (when known), track number (when known), and song title for audio filenames.

When the album is known:

`Artist - Album - NN - Song Name.mp3`

When the album is unknown:

`Artist - Song Name.mp3`

When the album is known but the track number is unknown, omit the track number:

`Artist - Album - Song Name.mp3`
Filename validity:

- Filenames must be valid on Windows. Remove or safely normalize forbidden characters such as `:`, `*`, `?`, `"`, `<`, `>`, `|`, and `/` (use `_` for a slash when needed, such as `AC_DC`).
- A filename that omits an illegal punctuation mark (for example, `Presents: Jock Jams` becoming `Presents Jock Jams`) is valid when the artist, album, track number, and title otherwise match. Validation must not flag that normalization as a mismatch.
- Validation should compare a normalized form, so harmless terminal-period differences in credited names (for example, `T.I.` versus `T.I`) and approved duplicate qualifiers such as `(2)` do not create false positives.
- Preserve official artist styling in metadata even when a symbol is illegal in filenames. For example, keep `*NSYNC` in MP3 tags but use `NSYNC` in the filename.



- Zero-pad track numbers below 10 so album folders sort correctly.
- Use the track artist rather than the album artist. This means featured
  artists appear in the filename when they are part of the artist tag.
- Apply the same convention to MP3 and WMA files, including archived copies.
- When two distinct files in the same folder would otherwise receive the same
  name, retain a minimal album, version, or bitrate qualifier after the song
  name rather than overwriting either recording.

Keep labels such as `Clean`, `Remix`, `Single Version`, `Unreleased Version`,
and `Alternate Version` when they distinguish genuinely different audio.

### Artwork Policy

- Embed one verified front cover in every MP3 when its album is known and verified artwork is available.
- Keep one useful `Folder.jpg` in each album folder.
- A mixed folder may use a specifically named cover file rather than a
  misleading generic `Folder.jpg`.
- Do not assign album art to an unidentified, unreleased, or unofficial file
  merely to eliminate a missing-art result.
- Replace empty APIC frames with real art or remove the empty frame.
- Validate embedded art by reopening every updated file before removing old
  JPGs.
- For every artist-folder audit, explicitly report embedded-art presence for every
  MP3 and WMA, the matching album-folder `Folder.jpg` status, and any files
  that remain without verified artwork.
- After validation, redundant `AlbumArt_{GUID}_Large.jpg`,
  `AlbumArt_{GUID}_Small.jpg`, `AlbumArtSmall.jpg`, black placeholders, and
  legacy artwork archives can be deleted when the user has approved cleanup.
- Do not leave loose duplicate JPGs in the artist folder after an approved update. Keep only one useful `Folder.jpg` inside each applicable album folder; a singles folder may retain a specifically named cover instead.

### Duplicate and Quality Policy

- Do not delete audio merely because another encode appears better.
- Prefer the higher-bitrate copy only when the recordings clearly match.
- Preserve rejected encodes under an `Archive`, `Redundant Encodes`, or
  `Exact Duplicates` folder unless deletion is explicitly requested.
- Preserve remixes, clean versions, single versions, mashups, and unreleased
  recordings as distinct files.
- Never transcode a low-bitrate MP3 upward. Recommend finding a better source.
- Do not substitute a single edit or alternate recording for a missing album
  track when its duration does not match the album master.

## Completed Artist Work

The notes below describe the last verified state. Files may later be moved or
changed outside this workflow, so rescan before making new edits.

### 2 Live Crew

Historical work only. A `2 Live Crew` folder was not present at the music root
on 2026-08-23.

- Audited 17 MP3 files.
- Most files were actually by other artists rather than 2 Live Crew.
- Renamed all 17 files using their verified artist and title.
- Metadata was not changed during that pass.

If this folder returns, do not assume the files belong to 2 Live Crew based on
the directory name. Recheck the embedded artist and title first.

### 2Pac

Folder: `G:\My Drive\Music\2Pac`

Last verified state:

- 61 readable MP3 files.
- 50 files had embedded artwork.
- 11 files intentionally remained without artwork because a reliable exact
  release cover was not established.
- Filenames and core tags were normalized during the earlier update.
- Five verified covers were added to `Confessions`, `Holler If Ya Hear Me`,
  `I Wonder If Heaven Got a Ghetto`, `Lost Souls`, and `Pain`.
- `Pain` was corrected to album `Regulate`, year `1994`, track `3/4`, with
  album artist `Various Artists`.
- Standalone JPG files were no longer required after embedding and could be
  removed.

### Three Dog Night

Historical work only. A `3 Dog Night` folder was not present at the music root
on 2026-08-23.

- Audited and updated 13 MP3 files.
- Corrected the canonical artist from `3 Dog Night` to `Three Dog Night`.
- Renamed files to `Three Dog Night - Title.mp3`.
- Corrected titles, album metadata, year, and track information.
- Replaced empty APIC placeholders.
- Embedded a verified compilation cover in 12 compilation tracks.
- Replaced a black `Folder.jpg` with a real 1200-pixel cover.
- Identified `Jeremiah Was a Bullfrog` by duration/catalog as
  `Joy to the World (Single Edit)`, album `Joy to the World`, year `1971`.
- The single edit remained without embedded art because no reliable exact
  single cover was established.

### 311

Folder: `G:\My Drive\Music\311`

Last verified state after the completed update:

- 17 readable 311 MP3 files with 17 unique audio payloads.
- All files are organized into release folders and follow the known-album
  `Artist - Album - NN - Song Name.mp3` convention.
- Core artist, album artist, title, album, year, track, and genre tags were
  normalized.
- Six verified album covers are retained as `Folder.jpg` and embedded in 16
  confidently identified tracks.
- `Who's Got the Herb?` is filed as track `4/15` on the `Hempilation`
  compilation with album artist `Various Artists`. It remains without artwork
  because no reliable exact-release cover was available. The Windows filename
  omits the question mark, while the title tag retains it.
- `Slinky Girl` was corrected to `Slinky`, track `1/11` on `Unity` (1991).
- `I'll Be Here A While` was corrected to the official title
  `I'll Be Here Awhile`, track `12/12` on `From Chaos` (2001).
- Twelve redundant GUID-style JPG files were removed after artwork validation.
- One misplaced Taking Back Sunday file was moved to
  `Taking Back Sunday\Taking Back Sunday EP` and named
  `Taking Back Sunday - 03 - Eleven (Incomplete).mp3`. Its 1:54 duration is
  substantially shorter than the roughly 3:43 EP master, so it is explicitly
  preserved as incomplete and has no invented artwork.

Known low-bitrate 311 files that should be replaced only from genuine better
sources:

| File | Bitrate |
| --- | ---: |
| `311\311 - 05 - Hive.mp3` | 96 kbps |
| `From Chaos\311 - 12 - I'll Be Here Awhile.mp3` | 96 kbps |
| `Soundsystem\311 - 09 - Eons.mp3` | 96 kbps |
### 3 Doors Down

Folder: `G:\My Drive\Music\3 Doors Down`

The user instructed that the 12 WMA files should be treated as valid,
good-quality source material.

Current organization from the last update:

- `The Better Life`: 11 canonical 128 kbps WMA album tracks, numbered and
  tagged as the preferred complete album set.
- The twelfth WMA was an exact duplicate of `Life of My Own` and was preserved
  under `Archive\Exact Duplicates`.
- Redundant MP3 album encodes were normalized and retained under
  `Archive\Redundant Encodes`.
- `Away From the Sun`: active tracks 2 through 12, with corrected filenames,
  metadata, years, and track numbers.
- The 192 kbps `Going Down in Flames` was preferred over the 128 kbps encode.
- The 128 kbps `Here Without You` was preferred over the 96 kbps encode.
- `Bonus Track` was correctly identified as `This Time`, track `12/12`.
- Track 1, the 4:22 album master of `When I'm Gone`, is still missing.
- The 4:11 `Album Version` and 4:01 `Unreleased Version` were preserved under
  `Singles & Rarities`; neither was substituted for the missing album master.
- Verified covers were embedded in the album files, with one `Folder.jpg` in
  each album folder.
- Legacy JPGs were moved to `Archive\Legacy Artwork`. They are redundant and
  safe to remove after confirming the current album covers remain in place.

### 50 Cent

Folder: `G:\My Drive\Music\50 Cent`

Last verified state after the approved update:

- 55 readable MP3 files.
- 55 unique audio payloads; no exact audio duplicates.
- No MP3 files or JPG files remain loose in the artist-folder root.
- Artist casing, titles, album names, years, track numbers, genre, featured
  artists, filenames, and extensions were normalized.
- 34 confidently identified tracks have verified embedded artwork.
- Empty artwork frames were removed.
- Thirty legacy JPG files were replaced with eight purposeful cover files.
- No audio was deleted.

Folder counts:

| Folder | MP3 files |
| --- | ---: |
| Before I Self Destruct | 1 |
| Featured Appearances | 2 |
| Get Rich or Die Tryin' | 9 |
| God's Plan | 1 |
| Mixtapes & Unreleased | 11 |
| No Mercy, No Fear | 1 |
| Power of the Dollar | 2 |
| Singles & Remixes | 9 |
| The Massacre | 15 |
| The New Breed | 1 |
| The New Breed (Bootleg) | 3 |

Important 50 Cent decisions:

- `Magic Stick` is filed as `Lil' Kim feat. 50 Cent`, album
  `La Bella Mafia`, track `12/16`.
- `No Matta What (Party All Night)` is filed as
  `Toya feat. 50 Cent & Loon`, not as a primary 50 Cent song.
- `Ayo Technology` is labeled `Alternate Version` because its 4:33 duration
  does not match the standard 4:06 to 4:08 release.
- Both `Wanksta` alternates and the unofficial 2Pac remix were preserved.
- Production credits were removed from titles such as `Gunz Come Out`,
  `My Toy Soldier`, `Ski Mask Way`, `So Amazing`, and `This Is 50`.
- Uncertain bootleg and unreleased material was organized without fabricated
  album art or track numbers.

Known low-bitrate 50 Cent files that should be replaced only from better
sources:

| File | Bitrate |
| --- | ---: |
| `Get Rich or Die Tryin'\50 Cent - 06 - High All the Time.mp3` | 64 kbps |
| `Mixtapes & Unreleased\50 Cent - Baby Get on Your Knees.mp3` | 56 kbps |
| `Power of the Dollar\50 Cent feat. Destiny's Child - 12 - Thug Love.mp3` | 112 kbps |
| `The New Breed (Bootleg)\50 Cent feat. Eminem & Destiny's Child - 16 - Thug Love (Remix).mp3` | 96 kbps |

Do not upscale these files. Replace them only if a genuine higher-quality
source becomes available.

## Suggested Procedure for the Next Artist

1. Confirm the exact artist-folder name.
2. Run a read-only recursive inventory.
3. Audit metadata, audio quality, artwork, and payload hashes.
4. Report concrete recommendations if the user asks what should change.
5. When approved, build a complete source-to-destination mapping and preflight
   every path before editing.
6. Always apply corrected metadata, filenames, album-folder organization, and verified embedded artwork when the user has approved an update.
7. Reopen every modified file and verify its tags and embedded artwork.
8. Only then remove obsolete JPGs or legacy artwork folders, retaining useful `Folder.jpg` files as described above.
9. Report counts, preserved exceptions, missing album tracks, and remaining
   low-quality sources.

## Implementation Notes

- Environment is Windows PowerShell.
- Python plus Mutagen has been used temporarily for MP3 ID3 and WMA ASF tags.
- Install temporary dependencies under `%TEMP%`, then remove them and any
  helper scripts after validation.
- For MP3 duplicate checks, hash the MPEG audio payload without ID3v2 and ID3v1
  metadata so tag changes do not hide exact audio duplicates.
- WMA artwork uses the ASF `WM/Picture` field.
- Prefer MusicBrainz release data and Cover Art Archive front images.
- Always rescan after edits because files in this synced library may change
  outside the current session.

## Album-Art Exceptions
Before searching for album artwork, consult NO_ALBUM_ART.md. Directories listed there should not be repeatedly checked for album art unless new information is provided.




