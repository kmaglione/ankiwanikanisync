from __future__ import annotations

import re
from re import Pattern
from typing import TYPE_CHECKING, Any, Final, Self, Type, TypedDict

from requests_mock.mocker import Mocker

from ankiwanikanisync.wk_api import WK_API_BASE, wk

from .utils import forward_args

if TYPE_CHECKING:
    from http.cookiejar import CookieJar
    from io import IOBase
    from json import JSONEncoder

    from requests_mock.adapter import AdditionalMatcher, AnyMatcher, Callback, _Matcher
    from urllib3.response import HTTPResponse


class ResponseDict(TypedDict, total=False):
    status_code: int
    reason: str
    headers: dict[str, str]
    cookies: CookieJar | dict[str, str]
    json: Any | Callback[Any]
    text: str | Callback[str]
    content: bytes | Callback[bytes]
    body: IOBase | Callback[IOBase]
    raw: HTTPResponse | Callback[HTTPResponse]
    exc: Exception | Type[Exception]


type MaybeCallback[T] = T | Callback[T]


class SessionMock:
    BASE_URL: Final = WK_API_BASE

    def __init__(self, *, real_http: bool = False):
        self._mocker = Mocker(
            session=wk.session, real_http=real_http, case_sensitive=True
        )

    def __enter__(self) -> Self:
        self._mocker.__enter__()
        return self

    def __exit__(self, exc_type: type, exc_value, traceback) -> None:
        self._mocker.__exit__(exc_type, exc_value, traceback)

    def _request(
        self,
        method: str | AnyMatcher,
        url: str | Pattern[str],
        response_list: list[ResponseDict] | None = ...,
        *,
        request_headers: dict[str, str] = ...,
        complete_qs: bool = ...,
        status_code: int = ...,
        reason: str = ...,
        headers: dict[str, str] = ...,
        cookies: CookieJar | dict[str, str] = ...,
        json: MaybeCallback[Any] = ...,
        text: MaybeCallback[str] = ...,
        content: MaybeCallback[bytes] = ...,
        body: MaybeCallback[IOBase] = ...,
        raw: MaybeCallback[HTTPResponse] = ...,
        exc: MaybeCallback[Exception] = ...,
        additional_matcher: AdditionalMatcher = ...,
        json_encoder: Type[JSONEncoder] | None = ...,
    ) -> None: ...

    def _meth(
        self,
        url: str | Pattern[str],
        response_list: list[ResponseDict] | None = ...,
        *,
        request_headers: dict[str, str] = ...,
        complete_qs: bool = ...,
        status_code: int = ...,
        reason: str = ...,
        headers: dict[str, str] = ...,
        cookies: CookieJar | dict[str, str] = ...,
        json: MaybeCallback[Any] = ...,
        text: MaybeCallback[str] = ...,
        content: MaybeCallback[bytes] = ...,
        body: MaybeCallback[IOBase] = ...,
        raw: MaybeCallback[HTTPResponse] = ...,
        exc: MaybeCallback[Exception] = ...,
        additional_matcher: AdditionalMatcher = ...,
        json_encoder: Type[JSONEncoder] | None = ...,
    ) -> None: ...

    @forward_args(_request)
    def request(
        self, method: str | AnyMatcher, url: str | Pattern[str], *args, **kwargs
    ) -> _Matcher:
        if isinstance(url, Pattern):
            if not url.pattern.startswith("^"):
                raise ValueError("Regular expression must be anchored")
            pattern = f"^{re.escape(WK_API_BASE)}/{url.pattern[1:]}"
            url = re.compile(pattern)
        else:
            url = f"{WK_API_BASE}/{url}"
        return self._mocker.request(method, url, *args, **kwargs)

    @forward_args(_meth)
    def get(self, *args, **kwargs):
        return self.request("get", *args, **kwargs)

    @forward_args(_meth)
    def options(self, *args, **kwargs):
        return self.request("options", *args, **kwargs)

    @forward_args(_meth)
    def head(self, *args, **kwargs):
        return self.request("head", *args, **kwargs)

    @forward_args(_meth)
    def post(self, *args, **kwargs):
        return self.request("post", *args, **kwargs)

    @forward_args(_meth)
    def put(self, *args, **kwargs):
        return self.request("put", *args, **kwargs)

    @forward_args(_meth)
    def patch(self, *args, **kwargs):
        return self.request("patch", *args, **kwargs)

    @forward_args(_meth)
    def delete(self, *args, **kwargs):
        return self.request("delete", *args, **kwargs)
