from __future__ import annotations

import json
import base64
import hashlib
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import keyring


SERVICE = "PhotoEditor.Social"
GRAPH_VERSION = "v25.0"
GOOGLE_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
FACEBOOK_SCOPES = ("pages_show_list", "pages_read_engagement", "pages_manage_posts")
INSTAGRAM_SCOPES = ("instagram_business_basic", "instagram_business_content_publish")
CALLBACK_PATH = "/oauth/callback"
FACEBOOK_REDIRECT_URI = f"http://127.0.0.1:8765{CALLBACK_PATH}"


def _get(name: str, default: str = "") -> str:
    return keyring.get_password(SERVICE, name) or default


def _set(name: str, value: str) -> None:
    keyring.set_password(SERVICE, name, value)


def _json(name: str, default=None):
    value = _get(name)
    if not value:
        return {} if default is None else default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Saved social-account data is invalid ({name}). Reconnect the account.") from exc


def save_google_client(client: dict) -> None:
    root = client.get("installed") or client.get("web")
    if not isinstance(root, dict) or not root.get("client_id") or not root.get("token_uri"):
        raise ValueError("Choose a Google OAuth client-secrets JSON file with client_id and token_uri.")
    _set("google-client", json.dumps(root))


def save_meta_client(app_id: str, app_secret: str) -> None:
    if not app_id.strip() or not app_secret.strip():
        raise ValueError("Enter both the Meta App ID and App Secret.")
    _set("meta-client", json.dumps({"app_id": app_id.strip(), "app_secret": app_secret.strip()}))


def _http(method: str, url: str, body=None, headers=None, timeout=45):
    data = body
    request_headers = dict(headers or {})
    if isinstance(body, dict):
        data = urllib.parse.urlencode(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read()
            if response.headers.get_content_type() == "application/json":
                return json.loads(content.decode("utf-8")), response.headers
            return content, response.headers
    except urllib.error.HTTPError as exc:
        detail = exc.read(3000).decode("utf-8", "replace")
        raise RuntimeError(f"Social API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach the social platform: {exc.reason}") from exc


def _oauth_code(auth_url: str, redirect_uri: str, timeout=240) -> tuple[str, str]:
    parsed = urllib.parse.urlsplit(redirect_uri)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("The OAuth redirect must be a loopback address on this computer.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    state = secrets.token_urlsafe(24)
    result = {}
    received = threading.Event()

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            if urllib.parse.urlsplit(self.path).path != parsed.path or query.get("state", [""])[0] != state:
                self.send_error(400, "Invalid OAuth callback")
                return
            if "error" in query:
                result["error"] = query["error"][0]
            else:
                result["code"] = query.get("code", [""])[0]
            body = b"Authorization received. Return to PhotoEditor to continue."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            received.set()

        def log_message(self, *_args):
            return

    server = HTTPServer((parsed.hostname, port), Callback)
    if not parsed.port:
        redirect_uri = f"{parsed.scheme}://{parsed.hostname}:{server.server_port}{parsed.path}"
        auth_parts = urllib.parse.urlsplit(auth_url)
        auth_params = urllib.parse.parse_qs(auth_parts.query)
        auth_params["redirect_uri"] = [redirect_uri]
        auth_url = urllib.parse.urlunsplit(
            (auth_parts.scheme, auth_parts.netloc, auth_parts.path, urllib.parse.urlencode(auth_params, doseq=True), auth_parts.fragment)
        )
    server.timeout = 1
    separator = "&" if "?" in auth_url else "?"
    url = f"{auth_url}{separator}{urllib.parse.urlencode({'state': state})}"
    if not webbrowser.open(url):
        server.server_close()
        raise RuntimeError("Could not open the platform sign-in page in a browser.")
    deadline = time.monotonic() + timeout
    try:
        while not received.is_set() and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    if "error" in result:
        raise RuntimeError(f"Platform authorization was not completed: {result['error']}")
    if not result.get("code"):
        raise TimeoutError("Timed out waiting for the platform authorization callback.")
    return result["code"], redirect_uri


def _authorization_url(url: str, params: dict) -> str:
    return f"{url}?{urllib.parse.urlencode(params)}"


def _google_token_exchange(client: dict, code: str, redirect_uri: str, verifier: str) -> dict:
    token, _ = _http(
        "POST",
        client["token_uri"],
        {
            "code": code,
            "client_id": client["client_id"],
            "client_secret": client.get("client_secret", ""),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        },
    )
    return token


def _refresh_google_token(client: dict, token: dict) -> dict:
    if token.get("access_token") and float(token.get("expires_at", 0)) > time.time() + 60:
        return token
    if not token.get("refresh_token"):
        raise RuntimeError("YouTube sign-in has expired. Connect the account again.")
    renewed, _ = _http(
        "POST", client["token_uri"],
        {
            "client_id": client["client_id"],
            "client_secret": client.get("client_secret", ""),
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        },
    )
    token.update(renewed)
    token["expires_at"] = time.time() + float(renewed.get("expires_in", 3600))
    _set("youtube-token", json.dumps(token))
    return token


def connect_youtube() -> str:
    client = _json("google-client")
    if not client:
        raise ValueError("Configure the Google OAuth client-secrets JSON in Publish Settings first.")
    redirect_uri = "http://127.0.0.1:0/"
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    scope_params = {
        "response_type": "code",
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "scope": GOOGLE_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    code, redirect_uri = _oauth_code(
        _authorization_url(client.get("auth_uri", "https://accounts.google.com/o/oauth2/v2/auth"), scope_params),
        redirect_uri,
    )
    token = _google_token_exchange(client, code, redirect_uri, verifier)
    token["expires_at"] = time.time() + float(token.get("expires_in", 3600))
    _set("youtube-token", json.dumps(token))
    return "YouTube account connected"


def connect_instagram() -> str:
    client = _json("meta-client")
    if not client:
        raise ValueError("Configure a Meta App ID and App Secret in Publish Settings first.")
    redirect_uri = FACEBOOK_REDIRECT_URI
    scopes = " ".join(INSTAGRAM_SCOPES)
    auth_url = _authorization_url(
        "https://www.instagram.com/oauth/authorize",
        {
            "client_id": client["app_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
        },
    )
    code, _ = _oauth_code(auth_url, redirect_uri)
    token, _ = _http(
        "POST", "https://api.instagram.com/oauth/access_token",
        {
            "client_id": client["app_id"],
            "client_secret": client["app_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        },
    )
    access_token = token.get("access_token")
    if not access_token:
        raise RuntimeError("Instagram did not return an access token.")
    user, _ = _http(
        "GET",
        f"https://graph.instagram.com/{GRAPH_VERSION}/me?fields=user_id,username&access_token={urllib.parse.quote(access_token)}",
    )
    _set("instagram-token", access_token)
    _set("instagram-user-id", str(user["user_id"]))
    _set("instagram-username", str(user.get("username", "Instagram account")))
    return f"Connected Instagram account @{user.get('username', user['user_id'])}"


def connect_facebook() -> list[dict]:
    client = _json("meta-client")
    if not client:
        raise ValueError("Configure a Meta App ID and App Secret in Publish Settings first.")
    redirect_uri = FACEBOOK_REDIRECT_URI
    auth_url = _authorization_url(
        f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth",
        {
            "client_id": client["app_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(FACEBOOK_SCOPES),
        },
    )
    code, _ = _oauth_code(auth_url, redirect_uri)
    short, _ = _http(
        "GET",
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/oauth/access_token?"
        + urllib.parse.urlencode(
            {
                "client_id": client["app_id"],
                "client_secret": client["app_secret"],
                "redirect_uri": redirect_uri,
                "code": code,
            }
        ),
    )
    long, _ = _http(
        "GET",
        "https://graph.facebook.com/"
        + GRAPH_VERSION
        + "/oauth/access_token?"
        + urllib.parse.urlencode(
            {
                "grant_type": "fb_exchange_token",
                "client_id": client["app_id"],
                "client_secret": client["app_secret"],
                "fb_exchange_token": short["access_token"],
            }
        ),
    )
    accounts, _ = _http(
        "GET",
        f"https://graph.facebook.com/{GRAPH_VERSION}/me/accounts?"
        + urllib.parse.urlencode(
            {"fields": "id,name,access_token", "access_token": long["access_token"]}
        ),
    )
    pages = accounts.get("data", [])
    if not pages:
        raise RuntimeError("No Facebook Pages are available to this account with the requested permissions.")
    choices = []
    for page in pages:
        page_id = str(page["id"])
        _set(f"facebook-page-token-{page_id}", str(page["access_token"]))
        choices.append({"id": page_id, "name": str(page.get("name", page_id))})
    _set("facebook-pages", json.dumps(choices))
    return choices


def connected_accounts() -> dict:
    pages = _json("facebook-pages", [])
    return {
        "youtube": bool(_get("youtube-token")),
        "instagram": _get("instagram-username"),
        "facebook_pages": pages,
    }


def _youtube_access_token() -> str:
    client = _json("google-client")
    token = _json("youtube-token")
    if not client or not token:
        raise ValueError("Connect a YouTube account in Publish Settings first.")
    return _refresh_google_token(client, token)["access_token"]


def _request_youtube_upload(path: Path, details: dict) -> str:
    access_token = _youtube_access_token()
    metadata = {
        "snippet": {
            "title": details["title"][:100],
            "description": details["description"][:5000],
            "tags": [tag.strip() for tag in details.get("tags", "").split(",") if tag.strip()][:500],
            "categoryId": "22",
        },
        "status": {"privacyStatus": details.get("privacy", "private")},
    }
    start_url = (
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
    )
    response, headers = _http(
        "POST", start_url, json.dumps(metadata).encode("utf-8"),
        {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(path.stat().st_size),
        },
    )
    upload_url = headers.get("Location")
    if not upload_url:
        raise RuntimeError(f"YouTube did not create an upload session: {response}")

    offset, size, chunk_size = 0, path.stat().st_size, 8 * 1024 * 1024
    with path.open("rb") as stream:
        while offset < size:
            stream.seek(offset)
            chunk = stream.read(min(chunk_size, size - offset))
            request = urllib.request.Request(
                upload_url,
                data=chunk,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{offset + len(chunk) - 1}/{size}",
                },
                method="PUT",
            )
            try:
                with urllib.request.urlopen(request, timeout=180) as upload_response:
                    if upload_response.status in (200, 201):
                        payload = json.loads(upload_response.read().decode("utf-8"))
                        return f"https://www.youtube.com/watch?v={payload['id']}"
                    range_header = upload_response.headers.get("Range", "")
            except urllib.error.HTTPError as exc:
                if exc.code != 308:
                    detail = exc.read(3000).decode("utf-8", "replace")
                    raise RuntimeError(f"YouTube upload failed (HTTP {exc.code}): {detail}") from exc
                range_header = exc.headers.get("Range", "")
            if range_header.startswith("bytes=0-"):
                offset = int(range_header.rsplit("-", 1)[1]) + 1
            else:
                offset += len(chunk)
    raise RuntimeError("YouTube upload ended without a completed video response.")


def _facebook_upload(path: Path, details: dict) -> str:
    page_id = str(details.get("page_id", ""))
    token = _get(f"facebook-page-token-{page_id}")
    if not page_id or not token:
        raise ValueError("Connect Facebook and select a Page in Publish Settings first.")
    api_base = f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/video_reels"
    started, _ = _http("POST", api_base, {"upload_phase": "start", "access_token": token})
    video_id = str(started["video_id"])
    upload_url = started.get("upload_url") or f"https://rupload.facebook.com/video-upload/{GRAPH_VERSION}/{video_id}"
    size = path.stat().st_size
    def chunks():
        with path.open("rb") as stream:
            while True:
                data = stream.read(8 * 1024 * 1024)
                if not data:
                    break
                yield data

    request = urllib.request.Request(
        upload_url,
        data=chunks(),
        headers={
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(size),
            "Content-Type": "application/octet-stream",
            "Content-Length": str(size),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            upload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read(3000).decode("utf-8", "replace")
        raise RuntimeError(f"Facebook video upload failed (HTTP {exc.code}): {detail}") from exc
    if upload.get("success") is False:
        raise RuntimeError(f"Facebook rejected the uploaded video: {upload}")
    finished, _ = _http(
        "POST",
        api_base,
        {
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": details["description"][:5000],
            "access_token": token,
        },
    )
    if finished.get("success") is False:
        raise RuntimeError(f"Facebook could not publish the video: {finished}")
    return f"https://www.facebook.com/reel/{video_id}"


def _instagram_publish(path: Path, details: dict) -> str:
    token = _get("instagram-token")
    user_id = _get("instagram-user-id")
    public_url = details.get("public_url", "").strip()
    if not token or not user_id:
        raise ValueError("Connect a professional Instagram account in Publish Settings first.")
    parsed = urllib.parse.urlsplit(public_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Instagram publishing requires a public HTTPS URL for the reviewed MP4.")
    create, _ = _http(
        "POST",
        f"https://graph.instagram.com/{GRAPH_VERSION}/{user_id}/media",
        {
            "media_type": "REELS",
            "video_url": public_url,
            "caption": details["description"][:2200],
            "access_token": token,
        },
    )
    container_id = str(create["id"])
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        state, _ = _http(
            "GET",
            f"https://graph.instagram.com/{GRAPH_VERSION}/{container_id}?"
            + urllib.parse.urlencode({"fields": "status_code", "access_token": token}),
        )
        code = state.get("status_code")
        if code == "FINISHED":
            break
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram could not process the video: {state}")
        time.sleep(3)
    else:
        raise TimeoutError("Instagram processing took longer than five minutes. Check the account before retrying.")
    result, _ = _http(
        "POST",
        f"https://graph.instagram.com/{GRAPH_VERSION}/{user_id}/media_publish",
        {"creation_id": container_id, "access_token": token},
    )
    return f"https://www.instagram.com/reel/{result['id']}/"


def publish_video(platform: str, path: str | Path, details: dict) -> str:
    video = Path(path).expanduser().resolve()
    if not video.is_file() or video.suffix.casefold() != ".mp4":
        raise ValueError("Choose an existing MP4 export to publish.")
    if not details.get("title", "").strip():
        raise ValueError("Enter a post title.")
    if platform == "youtube":
        return _request_youtube_upload(video, details)
    if platform == "instagram":
        return _instagram_publish(video, details)
    if platform == "facebook":
        return _facebook_upload(video, details)
    raise ValueError(f"Unsupported publishing platform: {platform}")
