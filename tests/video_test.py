import sys
import tempfile
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.adjustment_stack import Adjustments
from processing.video_project import VideoProject, get_media_duration
from processing.video_render import (
    VIDEO_EXPORT_PROFILES,
    build_ffmpeg_command,
    export_video,
    ffmpeg_path,
)
from processing.montage import _motion_frame, _prepare_photo, generate_reel_video
from processing.photo_duplicates import collect_photo_paths, find_duplicate_groups
from processing.titles import render_title


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        photo_dir = root / "photos"
        photo_dir.mkdir()
        for index, color in enumerate(((190, 45, 25), (20, 65, 210))):
            Image.new("RGB", (96, 64), color).save(photo_dir / f"shot-{index}.png")
        pixels = np.zeros((96, 128, 3), dtype=np.uint8)
        pixels[..., 0] = np.arange(128, dtype=np.uint8)[None, :] * 2
        pixels[..., 1] = np.arange(96, dtype=np.uint8)[:, None] * 2
        pixels[..., 2] = 115
        original = photo_dir / "original-name.png"
        reencoded = photo_dir / "renamed-copy.jpg"
        unrelated = photo_dir / "unrelated.jpg"
        Image.fromarray(pixels).save(original)
        Image.fromarray(pixels).save(reencoded, quality=92)
        Image.new("RGB", (128, 96), (15, 30, 225)).save(unrelated, quality=92)
        duplicate_groups = find_duplicate_groups([original, reencoded, unrelated])
        assert len(duplicate_groups) == 1
        assert set(duplicate_groups[0].paths) == {original.resolve(), reencoded.resolve()}
        nested_folder = root / "photo-library" / "event"
        nested_folder.mkdir(parents=True)
        nested_photo = nested_folder / "nested.png"
        Image.new("RGB", (48, 32), (140, 100, 70)).save(nested_photo)
        assert nested_photo.resolve() in collect_photo_paths([root / "photo-library"], recursive=True)
        assert collect_photo_paths([root / "photo-library"], recursive=False) == []
        motion_source = np.broadcast_to(
            np.arange(128, dtype=np.uint8)[None, :, None], (96, 128, 3)
        ).copy()
        assert not np.array_equal(
            _motion_frame(motion_source, 0.0, "cinematic", 0),
            _motion_frame(motion_source, 1.0, "cinematic", 0),
        )
        edits = Adjustments()
        edits.exposure = 35
        original_preview = _prepare_photo(photo_dir / "shot-0.png", 96, 64)
        edited_preview = _prepare_photo(photo_dir / "shot-0.png", 96, 64, edits)
        assert int(edited_preview.mean()) > int(original_preview.mean())
        auto_edited_preview = _prepare_photo(
            photo_dir / "shot-0.png", 96, 64, auto_grade_photos=True
        )
        assert auto_edited_preview.shape == (64, 96, 3)
        assert not np.array_equal(original_preview, auto_edited_preview)

        music = root / "music.wav"
        samples = np.zeros(22050, dtype="<i2")
        with wave.open(str(music), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(22050)
            stream.writeframes(samples.tobytes())

        project = VideoProject(width=320, height=240, fps=10)
        base = project.add_media(photo_dir / "shot-0.png")
        base.duration = 1.0
        base.fade_in = 0.1
        title = project.add_title("A title overlay", duration=1.0)
        title.fade_in = 0.15
        title.fade_out = 0.15
        soundtrack = project.add_media(music, track=2)
        soundtrack.start = 0
        soundtrack.duration = 1.0
        soundtrack.source_in = 0.1
        soundtrack.fade_in = 0.1
        soundtrack.fade_out = 0.2
        title_path = root / "title.png"
        render_title(title.title, project.width, project.height).save(title_path)
        command = build_ffmpeg_command(
            project, root / "command-test.mp4", {title.clip_id: title_path}
        )
        filter_complex = command[command.index("-filter_complex") + 1]
        assert "format=rgba[base_working]" in filter_complex
        assert "atrim=start=0.1:duration=1" in filter_complex
        assert "afade=t=in:st=0:d=0.1" in filter_complex
        assert "afade=t=out:st=0.8:d=0.2" in filter_complex
        profile_expectations = {
            "h264": ("libx264", "yuv420p", "aac", "rgba"),
            "hevc-10bit": ("libx265", "yuv420p10le", "aac", "rgba64le"),
            "prores-422-hq": ("prores_ks", "yuv422p10le", "pcm_s24le", "rgba64le"),
        }
        for profile in VIDEO_EXPORT_PROFILES:
            destination = root / f"profile{profile.extension}"
            profile_command = build_ffmpeg_command(
                project, destination, {title.clip_id: title_path}, profile.key
            )
            command_text = " ".join(profile_command)
            assert profile_expectations[profile.key][0] in command_text
            assert profile_expectations[profile.key][1] in command_text
            assert profile_expectations[profile.key][2] in command_text
            if profile.key != "h264":
                assert f"format={profile_expectations[profile.key][3]}[base_working]" in (
                    profile_command[profile_command.index("-filter_complex") + 1]
                )
        try:
            build_ffmpeg_command(project, root / "wrong-extension.mp4", profile="prores-422-hq")
        except ValueError as exc:
            assert ".mov" in str(exc)
        else:
            raise AssertionError("A profile accepted an incompatible file extension.")

        save_path = root / "edit.videoedit"
        project.save(save_path)
        reloaded = VideoProject.load(save_path)
        assert len(reloaded.clips) == 3
        assert reloaded.clips[1].title == "A title overlay"

        exported = export_video(reloaded, root / "edited.mp4")
        assert exported.stat().st_size > 0
        protected_output = root / "protected.mp4"
        protected_output.write_bytes(b"previous complete export")
        invalid_project = VideoProject(width=320, height=240, fps=10)
        invalid_project.add_media(photo_dir / "shot-0.png").path = str(root / "missing.png")
        try:
            export_video(invalid_project, protected_output)
        except ValueError:
            pass
        else:
            raise AssertionError("An invalid render project was exported.")
        assert protected_output.read_bytes() == b"previous complete export"
        assert not list(root.glob(".protected.*.partial.mp4"))
        capture = cv2.VideoCapture(str(exported))
        try:
            assert capture.isOpened()
            assert capture.get(cv2.CAP_PROP_FRAME_COUNT) == 10
            assert capture.read()[0]
        finally:
            capture.release()

        audio_probe = __import__("subprocess").run(
            [ffmpeg_path(), "-hide_banner", "-i", str(exported)],
            capture_output=True, text=True, check=False,
        )
        assert "Video:" in audio_probe.stderr and "Audio:" in audio_probe.stderr
        for profile in ("hevc-10bit", "prores-422-hq"):
            definition = next(item for item in VIDEO_EXPORT_PROFILES if item.key == profile)
            master = export_video(reloaded, root / f"master{definition.extension}", profile)
            assert master.stat().st_size > 0
            probe = __import__("subprocess").run(
                [ffmpeg_path(), "-hide_banner", "-i", str(master)],
                capture_output=True, text=True, check=False,
            )
            expected_codec = "hevc" if profile == "hevc-10bit" else "prores"
            assert expected_codec in probe.stderr.lower()

        montage = generate_reel_video(
            photo_dir, root / "montage.mp4", fps=10,
            duration_per_photo=0.2, transition_duration=0.1,
            audio_path=music, width=320, height=240,
        )
        montage_probe = __import__("subprocess").run(
            [ffmpeg_path(), "-hide_banner", "-i", str(montage)],
            capture_output=True, text=True, check=False,
        )
        assert "audio:" in montage_probe.stderr.lower() and "video: h264" in montage_probe.stderr.lower()
        sequence = generate_reel_video(
            None, root / "sequence.mp4", photo_paths=[photo_dir / "shot-0.png", photo_dir / "shot-1.png"],
            fps=10, duration_per_photo=0.8, transition_duration=0,
            audio_path=music, width=320, height=240, template="Dynamic snap",
        )
        capture = cv2.VideoCapture(str(sequence))
        try:
            assert capture.isOpened()
            assert capture.get(cv2.CAP_PROP_FRAME_COUNT) == 16
        finally:
            capture.release()

        mp3 = root / "music.mp3"
        __import__("subprocess").run(
            [ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-i", str(music), "-y", str(mp3)],
            check=True,
        )
        assert 0.9 <= get_media_duration(mp3, "audio") <= 1.1

        silent_source = root / "silent-source.mp4"
        writer = cv2.VideoWriter(
            str(silent_source), cv2.VideoWriter_fourcc(*"mp4v"), 10, (96, 64)
        )
        assert writer.isOpened()
        for _ in range(10):
            writer.write(np.full((64, 96, 3), (50, 120, 200), dtype=np.uint8))
        writer.release()
        silent_project = VideoProject(width=320, height=240, fps=10)
        silent_clip = silent_project.add_media(silent_source)
        silent_clip.duration = 1.0
        silent_export = export_video(silent_project, root / "silent-source-export.mp4")
        assert silent_export.stat().st_size > 0
        try:
            generate_reel_video(
                photo_dir, root / "silent.mp4", fps=10,
                duration_per_photo=0.1, transition_duration=0,
                width=320, height=240,
            )
        except ValueError as exc:
            assert "must include audio" in str(exc)
        else:
            raise AssertionError("A montage without its required soundtrack was accepted.")
    print("VIDEO TEST OK")


if __name__ == "__main__":
    main()
