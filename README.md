# PhotoEditor

PhotoEditor is a Windows desktop photo and video editing suite built with Python, PySide6, Pillow, NumPy, OpenCV, and FFmpeg. Photo projects preserve the original source and store non-destructive adjustments. Video projects use editable multitrack timelines and export H.264 MP4 with AAC audio.

## Photo editing

- Import JPEG, PNG, TIFF, WebP, BMP, GIF, and camera RAW formats when RAW support is installed.
- Develop with exposure, tone, white balance, HSL, curves, colour grading, detail, lens correction, crop, masks, and retouch tools.
- Use Professional Batch Edit for mixed photo folders, and presets for reusable edits.
- Open Photo Catalog to index local shoots without copying or moving original files. Search camera, lens, date, keywords, ratings, review flags, and local focus/exposure hints; back up or restore catalog metadata independently from originals.
- Flag picks, needs-review photos, or rejects with keyboard-first ratings. Search and sort by capture date, quality cue, review warnings, and rating; page through large shoots. Quality hints and visually similar-photo groups are recommendations only; PhotoEditor never automatically moves or deletes catalog photos.
- Export selected catalog photos with web, print, WebP, PNG, 8-bit TIFF, or 16-bit TIFF master recipes. Exports are written as new files into a separate edited-copies folder; optional on-device automatic editing and metadata inclusion are explicitly selectable. Location metadata is excluded unless you opt in.
- Create a photo video directly from the catalog selection; the selected sequence opens in the existing montage builder with duplicate review, motion templates, soundtrack, and aspect-ratio choices.
- Photo imports convert embedded raster colour profiles to sRGB when available. RAW and compatible sRGB 16-bit raster sources retain their 16-bit RGB channels through adjustments, geometric edits, batch processing, and `.photoedit` saves. Choose **16-bit TIFF · high-depth master** for a full-resolution 16-bit TIFF master; ordinary 8-bit files do not gain source detail. Non-sRGB 16-bit raster profiles use the established 8-bit color-managed path with a warning, rather than silently misinterpreting their colors. Web/social exports remain 8-bit and can embed an sRGB profile.
- The normal canvas uses an asynchronous display preview to reduce memory and CPU use. Choose **Workspace → Inspect at 100%** or **100% Detail** to render the edited image at its full source dimensions and inspect actual pixels; middle-drag to pan. **Fit Image** returns to the fast preview. The source is never reduced for export; full-resolution rendering can take substantially longer and use more memory for large RAW files.
- Export JPEG, PNG, TIFF, and WebP, or save an editable `.photoedit` project. High-depth project saves retain the decoded 16-bit source; RAW files are still demosaiced to sRGB for editing rather than stored as sensor-native RAW data.

## Video editing

Choose **Video Editor** from the suite launcher. Add still images and video to V1/V2 tracks and audio files to A1. The editable timeline supports clip start and source-in points, duration trimming, splitting at the playhead, audio gain, picture opacity, fade-in/fade-out, title overlays, project aspect ratio, and frame rate. Build a review preview and watch the composed sequence before export. Choose H.264 MP4 for broad playback compatibility, 10-bit HEVC MP4 for smaller high-quality delivery, or ProRes 422 HQ MOV as an intraframe editing master. High-bit-depth profiles composite in FFmpeg's 16-bit RGBA working format and encode to 10-bit video; source precision is limited by the bit depth of the media and edits already applied. Output is tagged Rec. 709. `.videoedit` projects save the edit and media paths; keep the source files available when reopening.

The Photo Editor and Video Editor each have a **Create video from photos** workflow that accepts individual files or folders (including subfolders). Images are compared from decoded pixels using perceptual hashes, so renamed or re-encoded visual copies can be identified. Review every detected group and choose to include all copies or keep one; no source photo is deleted. Templates include cinematic push, story drift, dynamic snap, and memory flash, with portrait, square, and landscape exports, animated stills, transitions, and a required soundtrack. Video Editor treats its selected photos as pre-edited and does not alter them. The full Suite optionally auto-edits each image according to its file type before video creation; this is separate from applying the current Photo Editor adjustments. RAW support requires the optional RAW decoder. The montage exports H.264 video with AAC audio. These are reusable social-friendly starting formats, not a claim about live platform trends. The Pixabay API does not provide an audio catalog, so audio discovery uses Freesound instead.

## Licensed audio

The built-in catalog searches Freesound CC0 1.0 sounds and sorts results by download count. Genres include ambient, cinematic, electronic, hip-hop, acoustic, orchestral, nature ambience, foley, impacts, and transitions. A personal Freesound API key is needed to search and download; PhotoEditor stores it in the Windows credential store. Downloaded files include a sidecar record with the creator, source URL, and license. The catalog does not claim to rank chart popularity or include copyrighted commercial hits. You may add your own audio files; verify rights for user-supplied content before publication.

## Social publishing

The publish dialog integrates the official YouTube Data API, Instagram Reels API, and Facebook Page Reels API. It requires your own Google OAuth client and Meta developer app credentials, which are stored with account tokens in the Windows credential store. YouTube defaults to **Private**. Instagram requires a professional account and a publicly accessible HTTPS video URL on hosting you configure; Facebook publishing is to a Page, not a personal profile. The app makes no post until you play the complete export, approve the post, and confirm **Publish now**.

The APIs are subject to account eligibility, platform app review/verification, requested permissions, rate limits, and policy changes. Setting credentials is not a substitute for platform approval. PhotoEditor does not include credentials, upload media automatically, or host Instagram media for you. Other social platforms are not currently integrated.

## Run from source

```bash
python -m pip install -r requirements.txt
python main.py
```

## Build three Windows executables

```bat
python -m pip install -r requirements-build.txt
build_windows.bat
```

The build creates:

- `dist\PhotoEditor-Photo.exe` — opens the photo workspace.
- `dist\PhotoEditor-Video.exe` — opens the video workspace.
- `dist\PhotoEditor-Suite.exe` — opens the workspace chooser.

All three are built from the same bundled runtime and media components; their startup mode is selected by executable name. They are standalone one-file Windows applications. The build script rejects any output larger than 16 GiB; recipients do not need Python installed. FFmpeg is bundled for video and audio processing.

## Tests

```bash
python tests/ui_test.py
python tests/smoke_test.py
python tests/feature_test.py
python tests/batch_test.py
python tests/catalog_test.py
python tests/video_test.py
python tests/social_test.py
python -m compileall -q app core image masks processing presets social ui tests
```

Social sign-in and uploads need real developer credentials and user approval, so the automated tests do not publish to external accounts.

## Project layout

- `app/` application startup, theme, and photo editor window
- `core/` photo documents, local catalog, history, projects, rendering, and automatic grading
- `image/` image loading, export, and metadata
- `processing/` image tools, montage, licensed audio, video projects, and rendering
- `social/` official OAuth and social publishing API clients
- `ui/` photo/video editors, audio catalog, help, and publishing review
- `presets/` saved photo adjustment presets
- `tests/` smoke, feature, batch, UI, and media-export checks
