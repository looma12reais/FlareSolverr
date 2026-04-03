import unittest
from base64 import b64decode
from typing import Any, Optional, cast

# pyright: reportGeneralTypeIssues=false, reportOptionalMemberAccess=false, reportOptionalSubscript=false, reportArgumentType=false, reportCallIssue=false, reportIndexIssue=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false
from fastapi.testclient import TestClient

from src import app, service, utils
from src.models import STATUS_ERROR, STATUS_OK, HealthResponse, IndexResponse, V1ResponseBase


class CompatTestClient:
    def __init__(self, app):
        self.client = TestClient(app)

    def get(self, path: str, status: int | None = None):
        response = self.client.get(path)
        if status is not None:
            assert response.status_code == status
        return response

    def post(self, path: str, json: Any | None = None, status: int | None = None):
        response = self.client.post(path, json=json)
        if status is not None:
            assert response.status_code == status
        return response

    def post_json(
        self, path: str, params: Any | None = None, status: int | None = None
    ):
        return self.post(path, json=params, status=status)


def _find_obj_by_key(
    key: str, value: str, _list: list[dict[str, Any]] | None
) -> Optional[dict[str, Any]]:
    if _list is None:
        return None

    for obj in _list:
        if obj[key] == value:
            return obj
    return None


def _require_int(value: int | None) -> int:
    assert value is not None
    return value


def _require_str(value: str | None) -> str:
    assert value is not None
    return value


def _require_solution(body: V1ResponseBase) -> Any:
    solution = body.solution
    assert solution is not None
    return solution


def _require_cookies(solution: Any) -> list[dict[str, Any]]:
    cookies = solution.cookies
    assert cookies is not None
    return cookies


class TestFlareSolverr(unittest.TestCase):
    proxy_url = "http://127.0.0.1:8888"
    proxy_socks_url = "socks5://127.0.0.1:1080"
    google_url = "https://www.google.com"
    post_url = "https://httpbin.org/post"
    cloudflare_url = "https://nowsecure.nl/"
    cloudflare_url_2 = "https://idope.se/torrent-list/harry/"
    ddos_guard_url = "https://www.litres.ru/"
    fairlane_url = "https://www.pararius.com/apartments/amsterdam"
    custom_cloudflare_url = "https://www.muziekfabriek.org/"
    cloudflare_blocked_url = (
        "https://cpasbiens3.fr/index.php?do=search&subaction=search"
    )

    app = CompatTestClient(app.app)
    # wait until the server is ready
    app.get("/")

    def test_wrong_endpoint(self):
        res = self.app.get("/wrong", status=404)
        self.assertEqual(res.status_code, 404)

        body = res.json()
        self.assertEqual("Not found: '/wrong'", body["error"])
        self.assertEqual(404, body["status_code"])

    def test_index_endpoint(self):
        res = self.app.get("/")
        self.assertEqual(res.status_code, 200)

        body = IndexResponse(res.json())
        self.assertEqual("FlareSolverr is ready!", _require_str(body.msg))
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))
        self.assertIn("Chrome/", _require_str(body.userAgent))

    def test_health_endpoint(self):
        res = self.app.get("/health")
        self.assertEqual(res.status_code, 200)

        body = HealthResponse(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))

    def test_detect_text_content_type(self):
        self.assertTrue(
            service._is_text_content_type({"Content-Type": "text/html"})
        )
        self.assertTrue(
            service._is_text_content_type(
                {"content-type": "application/json; charset=utf-8"}
            )
        )
        self.assertFalse(
            service._is_text_content_type({"Content-Type": "image/png"})
        )

    def test_decode_binary_body_as_base64(self):
        payload = b"\x89PNG\r\n\x1a\nbinary"
        encoded = service.b64encode(payload).decode("ascii")
        self.assertEqual(payload, b64decode(encoded))

    def test_v1_endpoint_wrong_cmd(self):
        res = self.app.post("/v1", json={"cmd": "request.bad", "url": self.google_url})
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_ERROR, _require_str(body.status))
        self.assertEqual(
            "Error: Request parameter 'cmd' = 'request.bad' is invalid.",
            _require_str(body.message),
        )
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

    def test_v1_endpoint_request_get_no_cloudflare(self):
        res = self.app.post("/v1", json={"cmd": "request.get", "url": self.google_url})
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.google_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn("<title>Google</title>", _require_str(solution.response))
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

    def test_v1_endpoint_request_get_disable_resources(self):
        res = self.app.post(
            "/v1",
            json={"cmd": "request.get", "url": self.google_url, "disableMedia": True},
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.google_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn("<title>Google</title>", _require_str(solution.response))
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

    def test_v1_endpoint_request_get_cloudflare_js_1(self):
        res = self.app.post_json(
            "/v1", params={"cmd": "request.get", "url": self.cloudflare_url}
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge solved!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.cloudflare_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn("<title>nowSecure</title>", _require_str(solution.response))
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

        cf_cookie = _find_obj_by_key("name", "cf_clearance", _require_cookies(solution))
        self.assertIsNotNone(cf_cookie, "Cloudflare cookie not found")
        self.assertGreater(len(cast(dict[str, Any], cf_cookie)["value"]), 30)

    def test_v1_endpoint_request_get_cloudflare_js_2(self):
        res = self.app.post_json(
            "/v1", params={"cmd": "request.get", "url": self.cloudflare_url_2}
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge solved!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.cloudflare_url_2, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn(
            "<title>harry - idope torrent search</title>",
            _require_str(solution.response),
        )
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

        cf_cookie = _find_obj_by_key("name", "cf_clearance", _require_cookies(solution))
        self.assertIsNotNone(cf_cookie, "Cloudflare cookie not found")
        self.assertGreater(len(cast(dict[str, Any], cf_cookie)["value"]), 30)

    def test_v1_endpoint_request_get_ddos_guard_js(self):
        res = self.app.post_json(
            "/v1", params={"cmd": "request.get", "url": self.ddos_guard_url}
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge solved!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.ddos_guard_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn("<title>Литрес", _require_str(solution.response))
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

        cf_cookie = _find_obj_by_key("name", "__ddg1_", _require_cookies(solution))
        self.assertIsNotNone(cf_cookie, "DDOS-Guard cookie not found")
        self.assertGreater(len(cast(dict[str, Any], cf_cookie)["value"]), 10)

    def test_v1_endpoint_request_get_fairlane_js(self):
        res = self.app.post_json(
            "/v1", params={"cmd": "request.get", "url": self.fairlane_url}
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge solved!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.fairlane_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn(
            "<title>Rental Apartments Amsterdam</title>",
            _require_str(solution.response),
        )
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

        cf_cookie = _find_obj_by_key("name", "fl_pass_v2_b", _require_cookies(solution))
        self.assertIsNotNone(cf_cookie, "Fairlane cookie not found")
        self.assertGreater(len(cast(dict[str, Any], cf_cookie)["value"]), 50)

    def test_v1_endpoint_request_get_custom_cloudflare_js(self):
        res = self.app.post_json(
            "/v1", params={"cmd": "request.get", "url": self.custom_cloudflare_url}
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge solved!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.custom_cloudflare_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn(
            "<title>MuziekFabriek : Aanmelden</title>", _require_str(solution.response)
        )
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

        cf_cookie = _find_obj_by_key(
            "name", "ct_anti_ddos_key", _require_cookies(solution)
        )
        self.assertIsNotNone(cf_cookie, "Custom Cloudflare cookie not found")
        self.assertGreater(len(cast(dict[str, Any], cf_cookie)["value"]), 10)

    def test_v1_endpoint_request_get_cloudflare_blocked(self):
        res = self.app.post_json(
            "/v1",
            params={"cmd": "request.get", "url": self.cloudflare_blocked_url},
            status=500,
        )
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_ERROR, _require_str(body.status))
        self.assertEqual(
            "Error: Error solving the challenge. Cloudflare has blocked this request. "
            "Probably your IP is banned for this site, check in your web browser.",
            _require_str(body.message),
        )
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

    def test_v1_endpoint_request_get_cookies_param(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.get",
                "url": self.google_url,
                "cookies": [
                    {"name": "testcookie1", "value": "testvalue1"},
                    {"name": "testcookie2", "value": "testvalue2"},
                ],
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.google_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn("<title>Google</title>", _require_str(solution.response))
        self.assertGreater(len(_require_cookies(solution)), 1)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

        user_cookie1 = _find_obj_by_key(
            "name", "testcookie1", _require_cookies(solution)
        )
        self.assertIsNotNone(user_cookie1, "User cookie 1 not found")
        self.assertEqual("testvalue1", cast(dict[str, Any], user_cookie1)["value"])

        user_cookie2 = _find_obj_by_key(
            "name", "testcookie2", _require_cookies(solution)
        )
        self.assertIsNotNone(user_cookie2, "User cookie 2 not found")
        self.assertEqual("testvalue2", cast(dict[str, Any], user_cookie2)["value"])

    def test_v1_endpoint_request_get_returnOnlyCookies_param(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.get",
                "url": self.google_url,
                "returnOnlyCookies": True,
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.google_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertIsNone(solution.headers)
        self.assertIsNone(solution.response)
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

    def test_v1_endpoint_request_get_proxy_http_param(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.get",
                "url": self.google_url,
                "proxy": {"url": self.proxy_url},
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.google_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn("<title>Google</title>", _require_str(solution.response))
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

    def test_v1_endpoint_request_get_proxy_http_param_with_credentials(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.get",
                "url": self.google_url,
                "proxy": {
                    "url": self.proxy_url,
                    "username": "testuser",
                    "password": "testpass",
                },
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.google_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn("<title>Google</title>", _require_str(solution.response))
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

    def test_v1_endpoint_request_get_proxy_socks_param(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.get",
                "url": self.google_url,
                "proxy": {"url": self.proxy_socks_url},
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.google_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn("<title>Google</title>", _require_str(solution.response))
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

    def test_v1_endpoint_request_get_proxy_wrong_param(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.get",
                "url": self.google_url,
                "proxy": {"url": "http://127.0.0.1:43210"},
            },
            status=500,
        )
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_ERROR, _require_str(body.status))
        self.assertIn(
            "Error: Error solving the challenge. Message: unknown error: net::ERR_PROXY_CONNECTION_FAILED",
            _require_str(body.message),
        )
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

    def test_v1_endpoint_request_get_fail_timeout(self):
        res = self.app.post_json(
            "/v1",
            params={"cmd": "request.get", "url": self.google_url, "maxTimeout": 10},
            status=500,
        )
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_ERROR, _require_str(body.status))
        self.assertEqual(
            "Error: Error solving the challenge. Timeout after 0.01 seconds.",
            _require_str(body.message),
        )
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

    def test_v1_endpoint_request_get_fail_bad_domain(self):
        res = self.app.post_json(
            "/v1",
            params={"cmd": "request.get", "url": "https://www.google.combad"},
            status=500,
        )
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_ERROR, _require_str(body.status))
        self.assertIn(
            "Message: unknown error: net::ERR_NAME_NOT_RESOLVED",
            _require_str(body.message),
        )

    def test_v1_endpoint_request_get_deprecated_param(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.get",
                "url": self.google_url,
                "userAgent": "Test User-Agent",
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))

    def test_v1_endpoint_request_post_no_cloudflare(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.post",
                "url": self.post_url,
                "postData": "param1=value1&param2=value2",
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.post_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn(
            '"form": {\n    "param1": "value1", \n    "param2": "value2"\n  }',
            _require_str(solution.response),
        )
        self.assertEqual(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

    def test_v1_endpoint_request_post_cloudflare(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.post",
                "url": self.cloudflare_url,
                "postData": "param1=value1&param2=value2",
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge solved!", _require_str(body.message))
        self.assertGreater(_require_int(body.startTimestamp), 10000)
        self.assertGreaterEqual(
            _require_int(body.endTimestamp), _require_int(body.startTimestamp)
        )
        self.assertEqual(utils.get_flaresolverr_version(), _require_str(body.version))

        solution = _require_solution(body)
        self.assertIn(self.cloudflare_url, _require_str(solution.url))
        self.assertEqual(solution.status, 200)
        self.assertEqual(len(solution.headers), 0)
        self.assertIn("<title>405 Not Allowed</title>", _require_str(solution.response))
        self.assertGreater(len(_require_cookies(solution)), 0)
        self.assertIn("Chrome/", _require_str(solution.userAgent))

        cf_cookie = _find_obj_by_key("name", "cf_clearance", _require_cookies(solution))
        self.assertIsNotNone(cf_cookie, "Cloudflare cookie not found")
        self.assertGreater(len(cast(dict[str, Any], cf_cookie)["value"]), 30)

    def test_v1_endpoint_request_post_fail_no_post_data(self):
        res = self.app.post_json(
            "/v1", params={"cmd": "request.post", "url": self.google_url}, status=500
        )
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_ERROR, _require_str(body.status))
        self.assertIn(
            "Request parameter 'postData' is mandatory in 'request.post' command",
            _require_str(body.message),
        )

    def test_v1_endpoint_request_post_deprecated_param(self):
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.post",
                "url": self.google_url,
                "postData": "param1=value1&param2=value2",
                "userAgent": "Test User-Agent",
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Challenge not detected!", _require_str(body.message))

    def test_v1_endpoint_sessions_create_without_session(self):
        res = self.app.post_json("/v1", {"cmd": "sessions.create"})
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Session created successfully.", _require_str(body.message))
        self.assertIsNotNone(body.session)

    def test_v1_endpoint_sessions_create_with_session(self):
        res = self.app.post_json(
            "/v1", params={"cmd": "sessions.create", "session": "test_create_session"}
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Session created successfully.", _require_str(body.message))
        self.assertEqual(body.session, "test_create_session")

    def test_v1_endpoint_sessions_create_with_proxy(self):
        res = self.app.post_json(
            "/v1", params={"cmd": "sessions.create", "proxy": {"url": self.proxy_url}}
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("Session created successfully.", _require_str(body.message))
        self.assertIsNotNone(body.session)

    def test_v1_endpoint_sessions_list(self):
        self.app.post_json(
            "/v1", params={"cmd": "sessions.create", "session": "test_list_sessions"}
        )
        res = self.app.post_json("/v1", params={"cmd": "sessions.list"})
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("", _require_str(body.message))
        self.assertGreaterEqual(len(cast(list[str], body.sessions)), 1)
        self.assertIn("test_list_sessions", cast(list[str], body.sessions))

    def test_v1_endpoint_sessions_destroy_existing_session(self):
        self.app.post_json(
            "/v1", params={"cmd": "sessions.create", "session": "test_destroy_sessions"}
        )
        res = self.app.post_json(
            "/v1",
            params={"cmd": "sessions.destroy", "session": "test_destroy_sessions"},
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))
        self.assertEqual("The session has been removed.", _require_str(body.message))

    def test_v1_endpoint_sessions_destroy_non_existing_session(self):
        res = self.app.post_json(
            "/v1",
            params={"cmd": "sessions.destroy", "session": "non_existing_session_name"},
            status=500,
        )
        self.assertEqual(res.status_code, 500)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_ERROR, _require_str(body.status))
        self.assertEqual(
            "Error: The session doesn't exist.", _require_str(body.message)
        )

    def test_v1_endpoint_request_get_with_session(self):
        self.app.post_json(
            "/v1", params={"cmd": "sessions.create", "session": "test_request_sessions"}
        )
        res = self.app.post_json(
            "/v1",
            params={
                "cmd": "request.get",
                "session": "test_request_sessions",
                "url": self.google_url,
            },
        )
        self.assertEqual(res.status_code, 200)

        body = V1ResponseBase(res.json())
        self.assertEqual(STATUS_OK, _require_str(body.status))


if __name__ == "__main__":
    unittest.main()
