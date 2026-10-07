from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
)


HELP_TOPICS = {
    "Getting started": """
        <h1>Getting started</h1>
        <p>Open an image with <b>Open</b> on the toolbar or <b>File → Open…</b>.
        Choose a single photo, including a supported camera RAW file. The original
        file is never overwritten.</p>
        <p>Use <b>Auto Edit</b> for a complete editable starting point, or adjust
        the controls in Develop. Save your work as a <code>.photoedit</code>
        project to reopen it with its adjustments later. Use <b>Export</b> to
        create a finished image file.</p>
    """,
    "File and project": """
        <h1>File and project</h1>
        <ul>
        <li><b>Open…</b> — load one supported image for editing.</li>
        <li><b>Photo Catalog</b> — search shoots, maintain local ratings and review flags, and export separate edited copies.</li>
        <li><b>Open Project…</b> — reopen a PhotoEditor <code>.photoedit</code>
        project and its non-destructive adjustments.</li>
        <li><b>Save Project</b> — store the original image and current edits in a
        project file. It does not export a flattened image.</li>
        <li><b>Export…</b> — render edits to JPEG, PNG, TIFF, or WebP. The
        16-bit TIFF master preserves supported RAW/16-bit input precision;
        8-bit sources do not gain detail by choosing it.</li>
        <li><b>Save Preset… / Manage Presets…</b> — save, apply, and remove
        reusable adjustment settings.</li>
        <li><b>Exit</b> closes the editor; PhotoEditor warns if the project has
        unsaved edits.</li>
        </ul>
    """,
    "Toolbar and viewing": """
        <h1>Toolbar and viewing</h1>
        <ul>
        <li><b>Open</b> loads an image. <b>Open Project</b> loads a saved edit.</li>
        <li><b>Save Project</b> saves editable work. <b>Export</b> creates the
        final rendered image.</li>
        <li><b>Professional Batch</b> edits a whole folder and exports edited
        copies to a separate folder.</li>
        <li><b>Reel Montage</b> creates a social-ready video from a photo folder
        directly in the Photo Editor; the Video Editor is not required.</li>
        <li><b>Auto Edit</b> applies a full editable image adjustment.
        <b>Auto Colour Grade</b> focuses on colour and tonal grading.</li>
        <li><b>Zoom + / Zoom -</b> change magnification; the mouse wheel also
        zooms. <b>Fit</b> fits the image to the canvas. Drag with the middle
        mouse button to pan.</li>
        <li><b>Before / After</b> toggles the unedited source preview.</li>
        <li><b>100% Detail</b> renders the original-size edited image in the
        canvas so a 1:1 view shows actual source pixels. Use middle-drag to pan;
        <b>Fit</b> returns to the fast display preview.</li>
        <li><b>Photo / Video Hub</b> switches between the available workspaces.</li>
        <li><b>Save Preset</b> stores the current settings as a reusable look;
        <b>Manage Presets</b> applies or removes saved looks.</li>
        </ul>
    """,
    "Develop: Basic and Detail": """
        <h1>Develop: Basic and Detail</h1>
        <p><b>Basic</b> controls exposure, contrast, highlight/shadow recovery,
        white/black points, white balance, saturation, and vibrance.</p>
        <p><b>Detail</b> controls texture, clarity, dehaze, sharpening, noise
        reduction, grain, vignette, lens correction, chromatic aberration, and
        distortion. Keep sharpening and noise reduction subtle for natural
        results.</p>
        <p>Changes update a preview scaled for the editor display to reduce
        memory and CPU use. Export always renders the full-resolution original
        with the selected adjustments; preview scaling never reduces export
        quality.</p>
        <p><b>Undo</b> and <b>Redo</b> restore recent committed adjustment
        states. <b>Reset Adjustments</b> clears edits and restores defaults.</p>
    """,
    "Develop: HSL, Curves, Grading": """
        <h1>Develop: HSL, Curves, Grading</h1>
        <ul>
        <li><b>HSL</b> adjusts hue, saturation, and luminance for individual
        colour ranges.</li>
        <li><b>Curves</b> edits the master tone curve or separate red, green,
        and blue channels. Add and move points to remap tonal values.</li>
        <li><b>Grading</b> adds colour to shadows, midtones, highlights, and the
        whole image. Blending controls tonal-range overlap; balance shifts
        emphasis between shadows and highlights.</li>
        </ul>
    """,
    "Geometry and crop": """
        <h1>Geometry and crop</h1>
        <p>Use the Geometry panel to rotate by 90 degrees, flip, or straighten
        with the rotation slider. Crop presets include original, square 1:1,
        landscape 4:3 / 16:9, and portrait 3:4. Choose <b>Interactive Crop</b>
        and drag a rectangle across the photo; press Escape to cancel.</p>
        <p><b>Reset Geometry</b> restores rotation, flips, and crop to their
        defaults.</p>
    """,
    "Masks and local adjustments": """
        <h1>Masks and local adjustments</h1>
        <p>Create a <b>Brush</b>, <b>Linear</b>, or <b>Radial</b> mask. Select
        a brush mask and choose <b>Paint Selected Brush</b>, then paint on the
        photo. Use the local sliders to change exposure, contrast, temperature,
        and saturation only inside the mask.</p>
        <p><b>Feather</b> softens mask edges, <b>Density</b> controls mask
        strength, and <b>Invert Selected</b> reverses the mask selection.</p>
    """,
    "Professional Batch Edit": """
        <h1>Professional Batch Edit</h1>
        <p>Open <b>Professional Batch</b> from the toolbar or File menu. Use
        <b>Choose photo folder…</b> to select a folder, then choose a separate
        output folder. The dialog reports how many supported photos it found.
        Enable <b>Include subfolders</b> to scan nested folders.</p>
        <p><b>Professional Auto Edit</b> applies image-type-aware adjustments to
        mixed RAW and raster folders. <b>Full Auto Edit</b> applies the automatic
        edit; <b>Auto Colour Grade</b> focuses on grading. <b>Current Preset</b>
        applies a chosen preset. <b>Reference Style</b> matches the style of the
        currently open, edited image.</p>
        <p>Pick JPEG quality and press <b>Start Batch</b>. Progress and failures
        are reported; source photos are left unchanged and edited copies go to
        the output folder. RAW support requires the bundled/installed rawpy
        component.</p>
    """,
    "Photo Catalog": """
        <h1>Photo Catalog</h1>
        <p>Choose <b>Add photo folder</b> to create a shoot. The catalog indexes
        photos in place; it stores paths, camera metadata, ratings, flags,
        keywords, and review hints in a local database. Originals are never
        copied, moved, or deleted by catalog actions.</p>
        <p>Search filenames, dates, camera, lens, keywords, and quality hints.
        Sort by capture date, a simple quality cue, review warnings, or rating.
        Rate selected photos with the 1–5 keys. Mark a <b>Pick</b>,
        <b>Needs review</b>, or <b>Reject</b>; reject means a review flag only,
        not a deletion. Local hints look for possible soft focus, deep shadows,
        clipped highlights, and visually similar photos. They are approximate;
        face and eye expressions are not analyzed in this version. The score is
        a convenience for triage, not an objective measure of photographic merit.</p>
        <p><b>Export selected</b> makes new copies outside the originals folder.
        Pick a Web JPEG, Print JPEG, WebP, PNG, or TIFF recipe and optionally
        apply on-device automatic editing. Metadata, which can include location,
        is omitted unless explicitly enabled. Back up the local catalog
        separately from your original image files; catalog backups do not
        contain the photographs.</p>
        <p><b>Create video from selected</b> passes your selected photos into
        the montage builder. The originals remain unchanged; the montage
        includes a second duplicate review and can add licensed audio.</p>
    """,
    "Reel Montage": """
        <h1>Reel Montage</h1>
        <p>Add individual photos or a folder (including subfolders) and choose
        a template: Cinematic push, Story drift, Dynamic snap, or Memory flash.
        Choose a soundtrack, aspect ratio, and frame rate. Photo files are
        checked for visual duplicates using decoded image content rather than
        filenames. You must choose for each group whether to include every copy
        or keep the first one; source photos are never deleted.</p>
        <p>Photo Editor can apply the current image's adjustments across the
        sequence. Video Editor expects its photos to be pre-edited and leaves
        them unchanged. The full Suite additionally offers optional automatic,
        file-type-aware editing before the video is built. Export uses H.264
        with AAC audio, and images are fitted to the chosen frame without
        stretching.</p>
    """,
    "Video Editor": """
        <h1>Video Editor</h1>
        <p>Open <b>Video Editor</b> from the Photo / Video Hub. For a finished
        photo sequence, choose <b>Create video from photos</b>: select several
        images or a folder, review visual duplicates, and use a motion template
        and soundtrack. This standalone workflow uses prepared photos only and
        never applies automatic edits. Add photos and
        video clips to V1 or V2, and music or sound effects to A1. Use the
        timeline table to set track number, timeline start, source in-point,
        duration, volume, opacity, and fade-in / fade-out. V2 overlays V1;
        title clips can be added on V2. <b>Split at Playhead</b> cuts the
        selected clip into two linked source ranges.</p>
        <p>Set sequence aspect ratio and frame rate, choose <b>Build Preview</b>
        to render a review copy, then play it in the monitor. <b>Export Video</b>
        creates an H.264 MP4 with AAC audio. Save an editable
        <code>.videoedit</code> project; its media paths must remain available.</p>
    """,
    "Licensed audio": """
        <h1>Licensed audio</h1>
        <p>The catalog searches Freesound for Creative Commons CC0 1.0 items
        only; search results are ordered by download count, not a popularity
        chart. Categories include ambient, cinematic, electronic, acoustic,
        orchestral, nature, foley, impacts, and transitions. A personal
        Freesound API key is required for catalog search and download. It is
        stored in the Windows credential store. Downloaded sounds include a
        local source and license record.</p>
        <p>You may also add your own audio files. The app cannot determine your
        rights to a user-supplied track; verify its license before publishing.</p>
    """,
    "Social publishing": """
        <h1>Social publishing</h1>
        <p>Publishing is available for YouTube, Instagram Reels, and Facebook
        Page Reels through each platform's official APIs. Add your own Google
        OAuth client and Meta app credentials in <b>Publish Settings</b>;
        credentials and tokens are kept in the Windows credential store.
        Platform verification, app review, account permissions, quotas, and
        policy restrictions still apply.</p>
        <p>Choose the final MP4, play it through to the end, review the caption,
        and check the approval box. <b>Publish now</b> then asks for a final
        confirmation. YouTube uploads directly and defaults to Private.
        Instagram requires an Instagram professional account and a public
        HTTPS URL for the reviewed video on hosting you configure. Facebook
        publishing targets Pages, not personal profiles. PhotoEditor does not
        upload automatically, host files publicly, or include third-party
        account credentials.</p>
    """,
    "Histogram and shortcuts": """
        <h1>Histogram and shortcuts</h1>
        <p>The histogram shows the red, green, and blue tonal distributions of
        the rendered preview. It is a guide to exposure and colour, not a
        clipping warning.</p>
        <ul>
        <li><b>Ctrl+O</b> open image; <b>Ctrl+Shift+O</b> open project.</li>
        <li><b>Ctrl+S</b> save project; <b>Ctrl+Shift+S</b> export image.</li>
        <li><b>Ctrl+Z / Ctrl+Y</b> undo / redo.</li>
        <li><b>Ctrl+Alt+B</b> professional batch; <b>Ctrl+Shift+M</b> montage.</li>
        <li><b>Ctrl+Alt+A</b> auto edit; <b>Ctrl+G</b> auto colour grade.</li>
        <li><b>B</b> before/after; <b>F</b> fit image; <b>Ctrl+Q</b> exit.</li>
        </ul>
    """,
}


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PhotoEditor Help")
        self.setMinimumSize(680, 460)
        self.resize(900, 620)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search help topics and controls…")
        self.topics = QListWidget()
        self.article = QTextBrowser()
        self.article.setOpenExternalLinks(False)
        self.article.setReadOnly(True)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.topics)
        splitter.addWidget(self.article)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Search by feature or choose a topic"))
        layout.addWidget(self.search)
        layout.addWidget(splitter, 1)

        self.search.textChanged.connect(self._filter_topics)
        self.topics.currentTextChanged.connect(self._show_topic)
        self._filter_topics("")

    def _filter_topics(self, query):
        query = query.strip().casefold()
        selected = self.topics.currentItem().text() if self.topics.currentItem() else None
        self.topics.clear()
        for title, content in HELP_TOPICS.items():
            if not query or query in title.casefold() or query in content.casefold():
                self.topics.addItem(title)
        matches = self.topics.findItems(selected, Qt.MatchExactly) if selected else []
        row = self.topics.row(matches[0]) if matches else 0
        if self.topics.count():
            self.topics.setCurrentRow(row)
        else:
            self.article.setHtml("<h1>No matching help</h1><p>Try another search term.</p>")

    def _show_topic(self, title):
        if title in HELP_TOPICS:
            self.article.setHtml(HELP_TOPICS[title])
