from queue import Queue
from appian_locust import AppianTaskSequence
from locust import User, SequentialTaskSet, task, events
from locust.clients import HttpSession
from requests.models import Response, Request, PreparedRequest
from typing import List, Tuple, Any, Optional, Type, AnyStr
from types import TracebackType
import requests


class CustomLocust(User):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if kwargs.get('integration_url'):
            self.client = HttpSession(kwargs.get('integration_url'), events.request_success, events.request_failure)
            if kwargs.get('record_mode'):
                setattr(self.client, 'record_mode', kwargs.get('record_mode'))
        else:
            self.client = MockClient()

    def get_request_list(self) -> list:
        return self.client.request_list

    def set_response(self, path: str, status_code: int, body: AnyStr, cookies: dict = None,  headers: dict = {}) -> None:
        self.client.set_response(path, status_code, body, cookies=cookies, headers=headers)

    def set_default_response(self, status_code: int, body: str) -> None:
        self.client.set_default_response(status_code, body)

    def enqueue_response(self, status_code: int, body: str) -> None:
        self.client.enqueue_response(status_code, body)


class NoOpReadCloser():
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.read_bytes = 0

    def close(self) -> None:
        pass

    def read(self, buffer: int) -> bytes:
        content = self.content[self.read_bytes:self.read_bytes+buffer]
        self.read_bytes += buffer
        return content


class MockClient:
    html_snippet = """
            </script><script src="/suite/tempo/ui/sail-client/sites-05d032ca6319b11b6fc9.cache.js?\
                appian_environment=sites">
            </script><script src="/suite/tempo/ui/sail-client/omnibox-05d032ca6319b11b6fc9.cache.js?\
                appian_environment=sites" defer="true">
            </script></body></html>
            """
    js_snippet = """
                ADERS=exports.LEGACY_FEATURE_FLAGS=exports.DEFAULT_FEATURE_FLAGS=undefined;
                var RAW_DEFAULT_FEATURE_FLAGS={};var RAW_LEGACY_FEATURE_FLAGS=RAW_DEFAULT_FEATURE_FLAGS&2147483647;
                var DEFAULT_FEATURE_FLAGS=exports.DEFAULT_FEATURE_FLAGS=RAW_DEFAULT_FEATURE_FLAGS.toString(16);
                var LEGACY_FEATURE_FLAGS=exports.LEGACY_FEATURE_FLAGS=RAW_LEGACY_FEATURE_FLAGS.toString(16);var
                """

    def __init__(self) -> None:
        self.cookies = {"JSESSIONID": "a", "__appianCsrfToken": "b",
                        "__appianMultipartCsrfToken": "c"}
        self.enqueue_cookies = {"JSESSIONID": "a"}
        self.request_list: List[Tuple[str, str]] = []
        self.response_dict: dict = {}
        self.default_response = MockResponse()
        self.default_response.status_code = 200
        self.default_response.content = str.encode("")
        self.default_response.cookies = requests.cookies.cookiejar_from_dict(self.cookies)

        # For feature toggles
        self.set_response("/suite/sites", 200, self.html_snippet)
        self.set_response("/suite/tempo/ui/sail-client/sites-05d032ca6319b11b6fc9.cache.js",
                          200, self.js_snippet.format("5802956083228348"))
        self.set_response("/ae/sites", 200, self.html_snippet.replace('/suite', '/ae'))
        self.set_response("/ae/tempo/ui/sail-client/sites-05d032ca6319b11b6fc9.cache.js",
                          200, self.js_snippet.format("5802956083228348"))

        self.dummy_responses: Queue = Queue()

    def _response(self, path: str, **kwargs: dict) -> 'MockResponse':
        if path in self.response_dict:
            resp = self.response_dict[path]
            self.cookies = resp.cookies
            return self.response_dict[path]
        return self.default_response

    def get(self, path: str, **kwargs: dict) -> 'MockResponse':
        self.request_list.append(("get", path))
        if not self.dummy_responses.empty():
            return self.dummy_responses.get()
        return self._response(path, **kwargs)

    def post(self, path: str, **kwargs: dict) -> 'MockResponse':
        self.request_list.append(("post", path))
        if not self.dummy_responses.empty():
            return self.dummy_responses.get()
        return self._response(path, **kwargs)

    def enqueue_response(self, status_code: int, body: str) -> None:
        response = self.make_response(status_code, body, cookies=self.enqueue_cookies)
        self.dummy_responses.put(response)

    def set_response(self, path: str, status_code: int, body: str, cookies: dict = None, headers: dict = {}) -> None:
        response = self.make_response(status_code, body, path=path, cookies=cookies, headers=headers)
        self.response_dict[path] = response

    def set_default_response(self, status_code: int, body: str) -> None:
        response = self.make_response(status_code, body)
        self.default_response = response

    def make_response(self, status_code: int, body: str, path: str = "", cookies: dict = None, headers: dict = {}) -> 'MockResponse':
        response = MockResponse()
        response.status_code = status_code
        content = str.encode(body)
        response.content = content
        response.raw = NoOpReadCloser(content)
        response.cookies = requests.cookies.cookiejar_from_dict(cookies) if cookies else self.cookies
        response.request = MockPreparedRequest()
        response.request.path_url = path
        response.headers = headers
        return response


class MockResponse(Response):
    def __enter__(self) -> 'MockResponse':
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    @property
    def content(self) -> Any:
        return self._content

    @content.setter
    def content(self, val: Any) -> None:
        self._content = val

    def failure(self, ignored: Any) -> None:
        pass


class MockPreparedRequest(PreparedRequest):
    @property
    def path_url(self) -> str:
        return self._path_url

    @path_url.setter
    def path_url(self, val: str) -> None:
        self._path_url = val


class SampleAppianTaskSequence(AppianTaskSequence):
    @task
    def first_task(self) -> None:
        pass

    @task
    def second_task(self) -> None:
        pass
