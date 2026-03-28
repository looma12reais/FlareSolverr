from __future__ import annotations

from typing import Any, NotRequired, TypedDict

STATUS_OK = "ok"
STATUS_ERROR = "error"


class CookieDict(TypedDict):
    # We index into `cookie["name"]` in the codebase, so make this required to
    # satisfy static type-checkers without changing runtime behavior.
    name: str

    # Everything else is optional and may vary depending on the source.
    value: NotRequired[str]
    domain: NotRequired[str]
    path: NotRequired[str]
    expiry: NotRequired[int]
    httpOnly: NotRequired[bool]
    secure: NotRequired[bool]
    sameSite: NotRequired[str]


class ProxyConfig(TypedDict, total=False):
    url: str
    username: str
    password: str


# Some call sites (and downstream helpers) still type `proxy` as a plain `dict`.
# Keep this alias flexible so DTOs remain compatible with those annotations.
ProxyLike = dict[str, Any]


class ChallengeResolutionResultT:
    url: str | None = None
    # selenium doesn't provide HTTP response status; code sets 200 currently
    status: int | None = None
    headers: dict[str, str] | None = None
    response: str | None = None
    # selenium `driver.get_cookies()` returns list[dict[str, Any]] (cookie-like dicts)
    cookies: list[dict[Any, Any]] | None = None
    userAgent: str | None = None
    screenshot: str | None = None
    turnstile_token: str | None = None

    def __init__(self, _dict: Any):
        # Accept dict payloads (what we normally deserialize from JSON) but also tolerate
        # already-instantiated DTOs or other objects with attributes.
        if isinstance(_dict, dict):
            self.__dict__.update(_dict)
        else:
            self.__dict__.update(getattr(_dict, "__dict__", {}))


class ChallengeResolutionT:
    status: str | None = None
    message: str | None = None
    result: ChallengeResolutionResultT | None = None

    def __init__(self, _dict: Any):
        # Accept dict payloads (what we normally deserialize from JSON) but also tolerate
        # already-instantiated DTOs or other objects with attributes.
        if isinstance(_dict, dict):
            self.__dict__.update(_dict)
        else:
            self.__dict__.update(getattr(_dict, "__dict__", {}))
        if self.result is not None:
            self.result = ChallengeResolutionResultT(self.result)


class V1RequestBase(object):
    # V1RequestBase
    cmd: str | None = None
    # client-provided cookies (iterated as dicts with `name`); see flaresolverr_service.py
    cookies: list[CookieDict] | None = None
    maxTimeout: int | None = None
    proxy: ProxyLike | None = None
    session: str | None = None
    session_ttl_minutes: int | None = None
    headers: Any | None = None  # deprecated v2.0.0, not used
    userAgent: Any | None = None  # deprecated v2.0.0, not used

    # V1Request
    url: str | None = None
    postData: str | None = None
    returnOnlyCookies: bool | None = None
    returnScreenshot: bool | None = None
    download: bool | None = None  # deprecated v2.0.0, not used
    returnRawHtml: bool | None = None  # deprecated v2.0.0, not used
    waitInSeconds: int | None = None
    # Optional resource blocking flag (blocks images, CSS, and fonts)
    disableMedia: bool | None = None
    # Optional when you've got a turnstile captcha that needs to be clicked after X number of Tab presses
    tabs_till_verify: int | None = None

    def __init__(self, _dict: Any):
        # Accept dict payloads (what we normally deserialize from JSON) but also tolerate
        # already-instantiated DTOs or other objects with attributes.
        if isinstance(_dict, dict):
            self.__dict__.update(_dict)
        else:
            self.__dict__.update(getattr(_dict, "__dict__", {}))


class V1ResponseBase(object):
    # V1ResponseBase
    status: str | None = None
    message: str | None = None
    session: str | None = None
    sessions: list[str] | None = None
    startTimestamp: int | None = None
    endTimestamp: int | None = None
    version: str | None = None

    # V1ResponseSolution
    solution: ChallengeResolutionResultT | None = None

    # hidden vars
    __error_500__: bool = False

    def __init__(self, _dict: Any):
        # Accept dict payloads (what we normally deserialize from JSON) but also tolerate
        # already-instantiated DTOs or other objects with attributes.
        if isinstance(_dict, dict):
            self.__dict__.update(_dict)
        else:
            self.__dict__.update(getattr(_dict, "__dict__", {}))

        if self.solution is not None:
            # `solution` could be a dict or already a `ChallengeResolutionResultT`
            self.solution = ChallengeResolutionResultT(self.solution)


class IndexResponse(object):
    msg: str | None = None
    version: str | None = None
    userAgent: str | None = None

    def __init__(self, _dict: Any):
        # Accept dict payloads (what we normally deserialize from JSON) but also tolerate
        # already-instantiated DTOs or other objects with attributes.
        if isinstance(_dict, dict):
            self.__dict__.update(_dict)
        else:
            self.__dict__.update(getattr(_dict, "__dict__", {}))


class HealthResponse(object):
    status: str | None = None

    def __init__(self, _dict: Any):
        # Accept dict payloads (what we normally deserialize from JSON) but also tolerate
        # already-instantiated DTOs or other objects with attributes.
        if isinstance(_dict, dict):
            self.__dict__.update(_dict)
        else:
            self.__dict__.update(getattr(_dict, "__dict__", {}))
