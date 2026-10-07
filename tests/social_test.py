import json
import sys
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from processing.audio_library import _is_cc0, search_cc0
from social import publishing


class SocialIntegrationTests(unittest.TestCase):
    def test_youtube_upload_uses_bearer_token(self):
        with tempfile.TemporaryDirectory() as temporary:
            video = Path(temporary) / "reviewed.mp4"
            video.write_bytes(b"video")
            captured = {}

            def start_upload(_method, _url, _body, headers):
                captured.update(headers)
                return {}, {}

            with patch("social.publishing._youtube_access_token", return_value="unit-test-token"), patch(
                "social.publishing._http", side_effect=start_upload
            ):
                with self.assertRaisesRegex(RuntimeError, "did not create an upload session"):
                    publishing._request_youtube_upload(
                        video, {"title": "Test", "description": "", "privacy": "private"}
                    )
            self.assertEqual(captured.get("Authorization"), "Bearer unit-test-token")

    def test_audio_catalog_filters_to_cc0_and_download_sort(self):
        response = {
            "results": [
                {"id": 3, "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"},
                {"id": 4, "license_url": "https://creativecommons.org/licenses/by/4.0/"},
            ]
        }
        with patch("processing.audio_library.get_api_token", return_value="test-api-key"), patch(
            "processing.audio_library._request_json", return_value=response
        ) as request:
            items = search_cc0("cinematic score")
        self.assertEqual([item["id"] for item in items], [3])
        url = request.call_args.args[0]
        self.assertIn("sort=downloads_desc", url)
        self.assertIn("license", url)
        self.assertTrue(_is_cc0(response["results"][0]["license_url"]))
        self.assertFalse(_is_cc0(response["results"][1]["license_url"]))

    def test_meta_reel_upload_streams_in_bounded_chunks(self):
        with tempfile.TemporaryDirectory() as temporary:
            media = Path(temporary) / "large.mp4"
            with media.open("wb") as file:
                file.truncate(8 * 1024 * 1024 + 9)
            api_results = iter([
                ({"video_id": "v123", "upload_url": "https://rupload.facebook.com/v123"}, None),
                ({"success": True}, None),
            ])
            captured = {}

            class Response:
                def __init__(self):
                    self.status = 200

                def read(self):
                    return b'{"success":true}'

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return False

            def fake_upload(request, timeout):
                self.assertIsNotNone(timeout)
                self.assertTrue(hasattr(request.data, "__iter__"))
                self.assertFalse(isinstance(request.data, (bytes, bytearray)))
                captured["length"] = sum(len(chunk) for chunk in request.data)
                return Response()

            with patch("social.publishing._get", side_effect=lambda name, default="": "token" if "facebook-page-token" in name else ""), patch(
                "social.publishing._http", side_effect=lambda *args, **kwargs: next(api_results)
            ), patch("social.publishing.urllib.request.urlopen", side_effect=fake_upload):
                url = publishing._facebook_upload(media, {"page_id": "page1", "description": "test"})
            self.assertEqual(captured["length"], media.stat().st_size)
            self.assertEqual(url, "https://www.facebook.com/reel/v123")

    def test_instagram_rejects_non_public_media_before_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            video = Path(temporary) / "reviewed.mp4"
            video.write_bytes(b"video")
            with patch("social.publishing._get", side_effect=lambda name, default="": "token" if name == "instagram-token" else "account"), patch(
                "social.publishing._http"
            ) as request:
                with self.assertRaisesRegex(ValueError, "public HTTPS URL"):
                    publishing._instagram_publish(video, {"public_url": "http://localhost/video.mp4", "description": ""})
                request.assert_not_called()

    def test_google_client_configuration_validates_shape_without_writing_secret(self):
        with patch("social.publishing._set") as save:
            publishing.save_google_client({"installed": {"client_id": "client", "token_uri": "https://oauth.example/token"}})
        saved = json.loads(save.call_args.args[1])
        self.assertEqual(saved["client_id"], "client")
        with self.assertRaisesRegex(ValueError, "client-secrets"):
            publishing.save_google_client({"installed": {}})

    def test_loopback_oauth_callback_binds_ephemeral_port_and_checks_state(self):
        browser_url = {}

        def fake_browser(url):
            browser_url["url"] = url
            params = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            redirect = params["redirect_uri"][0]
            callback = redirect + "?" + urllib.parse.urlencode({
                "code": "one-time-code",
                "state": params["state"][0],
            })
            thread = threading.Thread(
                target=lambda: urllib.request.urlopen(callback, timeout=5).read(),
                daemon=True,
            )
            thread.start()
            browser_url["thread"] = thread
            return True

        with patch("social.publishing.webbrowser.open", side_effect=fake_browser):
            code, redirect = publishing._oauth_code(
                "https://accounts.example/authorize?redirect_uri=http%3A%2F%2F127.0.0.1%3A0%2F",
                "http://127.0.0.1:0/",
                timeout=5,
            )
        browser_url["thread"].join(timeout=5)
        self.assertEqual(code, "one-time-code")
        self.assertTrue(redirect.startswith("http://127.0.0.1:"))
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(browser_url["url"]).query)
        self.assertEqual(query["redirect_uri"][0], redirect)


if __name__ == "__main__":
    unittest.main()
