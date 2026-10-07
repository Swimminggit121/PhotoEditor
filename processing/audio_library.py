from __future__ import annotations

import json
import mimetypes
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import keyring


SERVICE_NAME = "PhotoEditor.Freesound"
TOKEN_NAME = "api-token"
API_ROOT = "https://freesound.org/apiv2"
LICENSE_PATHS = {"/publicdomain/zero/1.0", "/licenses/zero/1.0"}
GENRES = {
    "Popular music": "music",
    "Ambient": "ambient music",
    "Cinematic": "cinematic music",
    "Electronic": "electronic music",
    "Hip-hop": "hip hop beat",
    "Acoustic": "acoustic music",
    "Orchestral": "orchestral music",
    "Nature": "nature ambience",
    "Foley": "foley sound effect",
    "Impacts": "impact sound effect",
    "Transitions": "transition whoosh",
    "User search": "",
}


def get_api_token() -> str:
    return keyring.get_password(SERVICE_NAME, TOKEN_NAME) or ""


def set_api_token(token: str) -> None:
    cleaned = token.strip()
    if cleaned:
        keyring.set_password(SERVICE_NAME, TOKEN_NAME, cleaned)
    else:
        try:
            keyring.delete_password(SERVICE_NAME, TOKEN_NAME)
        except keyring.errors.PasswordDeleteError:
            pass


def _is_cc0(license_url: str) -> bool:
    parsed = urllib.parse.urlsplit(license_url)
    return (
        parsed.hostname == "creativecommons.org"
        and parsed.path.casefold().rstrip("/") in LICENSE_PATHS
    )


def _request_json(url: str, token: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Token {token}", "User-Agent": "PhotoEditor/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(1024).decode("utf-8", "replace")
        raise RuntimeError(f"Freesound API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Freesound: {exc.reason}") from exc


def search_cc0(query: str, page: int = 1, token: str | None = None) -> list[dict]:
    auth = (token or get_api_token()).strip()
    if not auth:
        raise ValueError("Enter a Freesound API key in Audio Library settings to search.")
    term = query.strip() or "music"
    params = urllib.parse.urlencode(
        {
            "query": term,
            "filter": 'license:"Creative Commons 0"',
            "sort": "downloads_desc",
            "page": max(1, int(page)),
            "page_size": 20,
            "fields": "id,name,username,license,license_url,previews,tags,downloads,duration,url,description",
        }
    )
    payload = _request_json(f"{API_ROOT}/search/text/?{params}", auth)
    return [item for item in payload.get("results", []) if _is_cc0(str(item.get("license_url", "")))]


def download_cc0(sound: dict, destination: str | Path, token: str | None = None) -> Path:
    auth = (token or get_api_token()).strip()
    if not auth:
        raise ValueError("Enter a Freesound API key in Audio Library settings to download.")
    if not _is_cc0(str(sound.get("license_url", ""))):
        raise ValueError("This sound is not marked CC0 and cannot be downloaded through this catalog.")
    sound_id = int(sound["id"])
    request = urllib.request.Request(
        f"{API_ROOT}/sounds/{sound_id}/download/",
        headers={"Authorization": f"Token {auth}", "User-Agent": "PhotoEditor/1.0"},
    )
    folder = Path(destination).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", str(sound.get("name", "freesound")).strip()).strip("-._")
    target = folder / f"{stem[:80] or 'freesound'}-{sound_id}"
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            filename = response.headers.get_filename() or ""
            extension = Path(filename).suffix or mimetypes.guess_extension(response.headers.get_content_type()) or ".wav"
            path = target.with_suffix(extension)
            with path.open("wb") as stream:
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    stream.write(chunk)
    except urllib.error.HTTPError as exc:
        detail = exc.read(1024).decode("utf-8", "replace")
        raise RuntimeError(f"Freesound download failed (HTTP {exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not download sound: {exc.reason}") from exc
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("Freesound returned an empty audio download.")

    attribution = {
        "provider": "Freesound",
        "sound_id": sound_id,
        "name": sound.get("name"),
        "author": sound.get("username"),
        "license": "CC0 1.0",
        "license_url": sound.get("license_url"),
        "source_url": sound.get("url"),
    }
    path.with_suffix(path.suffix + ".license.json").write_text(
        json.dumps(attribution, indent=2), encoding="utf-8"
    )
    return path
