from __future__ import annotations

import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from dataclasses import dataclass

import imageio_ffmpeg

from processing.video_project import VideoProject, validate_project
from processing.titles import render_title


@dataclass(frozen=True)
class VideoExportProfile:
    key: str
    label: str
    extension: str
    video_options: tuple[str, ...]
    audio_options: tuple[str, ...]


VIDEO_EXPORT_PROFILES = (
    VideoExportProfile(
        "h264",
        "H.264 · Web / social (MP4)",
        ".mp4",
        ("-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p"),
        ("-c:a", "aac", "-b:a", "320k"),
    ),
    VideoExportProfile(
        "hevc-10bit",
        "HEVC 10-bit · High quality (MP4)",
        ".mp4",
        (
            "-c:v", "libx265", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1",
        ),
        ("-c:a", "aac", "-b:a", "320k"),
    ),
    VideoExportProfile(
        "prores-422-hq",
        "ProRes 422 HQ · Editing master (MOV)",
        ".mov",
        ("-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le", "-vendor", "apl0"),
        ("-c:a", "pcm_s24le"),
    ),
)

_VIDEO_PROFILES = {profile.key: profile for profile in VIDEO_EXPORT_PROFILES}


def ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def build_ffmpeg_command(
    project: VideoProject,
    output: str | Path,
    title_sources: dict[str, Path] | None = None,
    profile: str = "h264",
) -> list[str]:
    validate_project(project)
    output_path = Path(output).expanduser().resolve()
    try:
        export_profile = _VIDEO_PROFILES[profile]
    except KeyError as exc:
        raise ValueError(f"Unknown video export profile: {profile}") from exc
    if output_path.suffix.casefold() != export_profile.extension:
        raise ValueError(
            f"The {export_profile.label} profile requires a {export_profile.extension} output file."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title_sources = title_sources or {}
    visual_clips = [clip for clip in project.clips if clip.kind in {"image", "video", "title"}]
    inputs = []
    input_index: dict[str, int] = {}
    for clip in project.clips:
        if clip.clip_id in input_index:
            continue
        input_index[clip.clip_id] = len(input_index)
        inputs.append(clip)

    command = [ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y"]
    for clip in inputs:
        clip_path = str(title_sources[clip.clip_id]) if clip.kind == "title" else clip.path
        if clip.kind in {"image", "title"}:
            command += [
                "-loop", "1", "-framerate", str(project.fps),
                "-t", _number(clip.duration), "-i", clip_path,
            ]
        elif clip.kind == "video" and clip.source_in:
            command += ["-ss", _number(clip.source_in), "-t", _number(clip.duration), "-i", clip_path]
        elif clip.kind == "video":
            command += ["-t", _number(clip.duration), "-i", clip_path]
        else:
            command += ["-i", clip_path]

    total_duration = project.duration
    background = project.background.lstrip("#")
    filters = [
        f"color=c=0x{background}:s={project.width}x{project.height}:r={project.fps}:d={_number(total_duration)}[base]"
    ]
    high_precision = export_profile.key != "h264"
    working_format = "rgba64le" if high_precision else "rgba"
    filters.append(f"[base]format={working_format}[base_working]")
    current = "base_working"
    for index, clip in enumerate(sorted(visual_clips, key=lambda item: (item.track, item.start, item.clip_id))):
        source_index = input_index[clip.clip_id]
        start, end = _number(clip.start), _number(clip.end)
        stream = f"v{index}"
        filters.append(
            f"[{source_index}:v]trim=duration={_number(clip.duration)},"
            f"setpts=PTS-STARTPTS+{start}/TB,"
            f"scale={project.width}:{project.height}:force_original_aspect_ratio=decrease,"
            f"pad={project.width}:{project.height}:(ow-iw)/2:(oh-ih)/2:color=black@0,"
            f"fps={project.fps},format={working_format},"
            f"colorchannelmixer=aa={_number(clip.opacity)}"
            + (f",fade=t=in:st={start}:d={_number(clip.fade_in)}:alpha=1" if clip.fade_in else "")
            + (f",fade=t=out:st={_number(max(clip.start, clip.end - clip.fade_out))}:d={_number(clip.fade_out)}:alpha=1" if clip.fade_out else "")
            + f"[{stream}]"
        )
        result = f"mix{index}"
        filters.append(
            f"[{current}][{stream}]overlay=0:0:"
            f"enable='between(t,{start},{end})':eof_action=pass:shortest=0[{result}]"
        )
        current = result

    audio_streams = []
    audio_number = 0
    for clip in project.clips:
        source_index = input_index[clip.clip_id]
        if clip.kind == "audio":
            label = f"a{audio_number}"
            audio_filters = [
                f"atrim=start={_number(clip.source_in)}:duration={_number(clip.duration)}",
                "asetpts=PTS-STARTPTS",
                f"volume={_number(clip.volume)}",
            ]
            if clip.fade_in:
                audio_filters.append(f"afade=t=in:st=0:d={_number(clip.fade_in)}")
            if clip.fade_out:
                audio_filters.append(
                    f"afade=t=out:st={_number(max(0, clip.duration - clip.fade_out))}:d={_number(clip.fade_out)}"
                )
            audio_filters.append(f"adelay={max(0, int(round(clip.start * 1000)))}:all=1")
            filters.append(
                f"[{source_index}:a]{','.join(audio_filters)}[{label}]"
            )
            audio_streams.append(f"[{label}]")
            audio_number += 1
        elif clip.kind == "video" and clip.include_source_audio and _video_has_audio(clip.path):
            label = f"a{audio_number}"
            audio_filters = [
                f"atrim=duration={_number(clip.duration)}",
                "asetpts=PTS-STARTPTS",
                f"volume={_number(clip.volume)}",
            ]
            if clip.fade_in:
                audio_filters.append(f"afade=t=in:st=0:d={_number(clip.fade_in)}")
            if clip.fade_out:
                audio_filters.append(
                    f"afade=t=out:st={_number(max(0, clip.duration - clip.fade_out))}:d={_number(clip.fade_out)}"
                )
            audio_filters.append(f"adelay={max(0, int(round(clip.start * 1000)))}:all=1")
            filters.append(
                f"[{source_index}:a]{','.join(audio_filters)}[{label}]"
            )
            audio_streams.append(f"[{label}]")
            audio_number += 1

    video_map = f"[{current}]"
    if audio_streams:
        if len(audio_streams) == 1:
            audio_map = audio_streams[0]
        else:
            mix = f"{''.join(audio_streams)}amix=inputs={len(audio_streams)}:duration=longest:normalize=0[aout]"
            filters.append(mix)
            audio_map = "[aout]"
    else:
        audio_map = None
    command += ["-filter_complex", ";".join(filters), "-map", video_map]
    if audio_map:
        command += ["-map", audio_map, *export_profile.audio_options]
    else:
        command += ["-an"]
    command += [
        *export_profile.video_options,
        "-r", str(project.fps),
        "-t", _number(total_duration),
        "-color_primaries", "bt709", "-color_trc", "bt709",
        "-colorspace", "bt709", "-color_range", "tv",
    ]
    if export_profile.key != "prores-422-hq":
        command += ["-movflags", "+faststart"]
    command.append(str(output_path))
    return command


_AUDIO_STREAMS: dict[str, bool] = {}


def _video_has_audio(path: str) -> bool:
    if path in _AUDIO_STREAMS:
        return _AUDIO_STREAMS[path]
    result = subprocess.run(
        [ffmpeg_path(), "-hide_banner", "-i", path],
        capture_output=True, text=True, check=False,
    )
    found = bool(re.search(r"Stream #\d+:\d+.*?: Audio:", result.stderr))
    _AUDIO_STREAMS[path] = found
    return found


def export_video(project: VideoProject, output: str | Path, profile: str = "h264") -> Path:
    target = Path(output).expanduser().resolve()
    try:
        export_profile = _VIDEO_PROFILES[profile]
    except KeyError as exc:
        raise ValueError(f"Unknown video export profile: {profile}") from exc
    if target.suffix.casefold() != export_profile.extension:
        raise ValueError(
            f"The {export_profile.label} profile requires a {export_profile.extension} output file."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f".{target.stem}.{uuid.uuid4().hex}.partial{target.suffix}")
    with tempfile.TemporaryDirectory(prefix="photoeditor-titles-") as title_directory:
        title_sources = {}
        for clip in project.clips:
            if clip.kind == "title":
                title_path = Path(title_directory) / f"{clip.clip_id}.png"
                render_title(clip.title, project.width, project.height).save(title_path)
                title_sources[clip.clip_id] = title_path
        try:
            command = build_ffmpeg_command(project, staging, title_sources, profile)
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode:
                detail = (result.stderr or result.stdout).strip()
                raise RuntimeError(f"FFmpeg could not export the video: {detail[-2000:]}")
            if not staging.is_file() or staging.stat().st_size == 0:
                raise RuntimeError("FFmpeg reported success but did not create a video file.")
            staging.replace(target)
            return target
        finally:
            staging.unlink(missing_ok=True)


def mux_montage_audio(video_path: str | Path, audio_path: str | Path, output_path: str | Path, volume: float = 0.35) -> Path:
    video, audio, output = (Path(path).expanduser().resolve() for path in (video_path, audio_path, output_path))
    if not video.is_file() or not audio.is_file():
        raise ValueError("Choose an existing montage video and audio file.")
    if not 0 <= volume <= 2:
        raise ValueError("Audio volume must be between 0 and 200%.")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video), "-stream_loop", "-1", "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-filter:a", f"volume={_number(volume)}",
        "-shortest", "-movflags", "+faststart", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Could not add soundtrack: {(result.stderr or result.stdout).strip()[-2000:]}")
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Audio muxing finished without producing a video.")
    return output


def ffmpeg_error_is_missing_audio(exc: Exception) -> bool:
    return bool(re.search(r"(matches no streams|does not contain any stream|Stream specifier .* matches no streams)", str(exc), re.I))
