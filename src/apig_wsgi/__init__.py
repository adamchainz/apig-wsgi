from __future__ import annotations

import sys
import urllib
from base64 import b64decode, b64encode
from collections import defaultdict
from collections.abc import Iterable, Sequence
from io import BytesIO
from types import TracebackType
from typing import Any, Callable, Union
from urllib.parse import urlencode

from apig_wsgi.compat import WSGIApplication

__all__ = ("make_lambda_handler",)

DEFAULT_NON_BINARY_CONTENT_TYPE_PREFIXES: tuple[str, ...] = (
    "text/",
    "application/json",
    # application/problem+json - a draft standard for JSON error responses
    # https://datatracker.ietf.org/doc/html/draft-ietf-appsawg-http-problem-00#section-3
    "application/problem+json",
    # application/vnd.api+json - JSON:API specification
    # https://jsonapi.org/
    "application/vnd.api+json",
)

RESERVED_URI_CHARACTERS = r"!#$&'()*+,/:;=?@[]%"

_ExcInfoType = Union[
    tuple[type[BaseException], BaseException, TracebackType],
    tuple[None, None, None],
    None,
]


def make_lambda_handler(
    wsgi_app: WSGIApplication,
    binary_support: bool | None = None,
    non_binary_content_type_prefixes: Iterable[str] | None = None,
) -> Callable[[dict[str, Any], Any], dict[str, Any]]:
    """
    Turn a WSGI app callable into a Lambda handler function suitable for
    running on API Gateway.

    Parameters
    ----------
    wsgi_app : function
        WSGI Application callable
    binary_support : bool
        Whether to support returning APIG-compatible binary responses
    non_binary_content_type_prefixes : tuple of str
        Tuple of content type prefixes which should be considered "Non-Binary" when
        `binary_support` is True. This prevents apig_wsgi from unexpectedly encoding
        non-binary responses as binary.
    """
    if non_binary_content_type_prefixes is None:
        non_binary_prefixes_tuple = DEFAULT_NON_BINARY_CONTENT_TYPE_PREFIXES
    else:
        non_binary_prefixes_tuple = tuple(non_binary_content_type_prefixes)

    def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
        # ALB doesn't send a version, but requestContext will contain a key named 'elb'.
        if (
            "requestContext" in event
            and isinstance(event["requestContext"], dict)
            and "elb" in event["requestContext"]
        ):
            version = "alb"
        else:
            version = event.get("version", "1.0")

        if version in ("1.0", "alb"):
            environ = get_environ_v1(
                event,
                context,
                encode_query_params=(version == "1.0"),
            )
            if version == "1.0":
                # Binary support defaults to 'off' on version 1
                if binary_support is None:
                    event_binary_support = False
                else:
                    event_binary_support = binary_support
            else:
                # Binary support defaults to 'on' on ALBs
                if binary_support is None:
                    event_binary_support = True
                else:
                    event_binary_support = binary_support
            response: BaseResponse = V1Response(
                binary_support=event_binary_support,
                non_binary_content_type_prefixes=non_binary_prefixes_tuple,
                multi_value_headers=environ["apig_wsgi.multi_value_headers"],
            )
        elif version == "2.0":
            environ = get_environ_v2(event, context)
            response = V2Response(
                binary_support=True,
                non_binary_content_type_prefixes=non_binary_prefixes_tuple,
            )
        else:
            raise ValueError("Unknown version {!r}".format(event["version"]))
        result = wsgi_app(environ, response.start_response)
        response.consume(result)
        return response.as_apig_response()

    return handler


def get_environ_v1(
    event: dict[str, Any], context: Any, encode_query_params: bool
) -> dict[str, Any]:
    body = get_body(event)
    environ: dict[str, Any] = {
        "CONTENT_LENGTH": str(len(body)),
        "HTTP": "on",
        "PATH_INFO": urllib.parse.unquote(event["path"], encoding="iso-8859-1"),
        "REMOTE_ADDR": "127.0.0.1",
        "REQUEST_METHOD": event["httpMethod"],
        "SCRIPT_NAME": "",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "SERVER_NAME": "",
        "SERVER_PORT": "",
        "wsgi.errors": sys.stderr,
        "wsgi.input": BytesIO(body),
        "wsgi.multiprocess": False,
        "wsgi.multithread": False,
        "wsgi.run_once": False,
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "apig_wsgi.multi_value_headers": False,
    }

    if encode_query_params:
        safe_chars = ""
    else:
        safe_chars = RESERVED_URI_CHARACTERS

    # Multi-value query strings need explicit activation on ALB
    if "multiValueQueryStringParameters" in event:
        environ["QUERY_STRING"] = urlencode(
            # may be None when testing on console
            event["multiValueQueryStringParameters"] or (),
            doseq=True,
            safe=safe_chars,
        )
    else:
        environ["QUERY_STRING"] = urlencode(
            event.get("queryStringParameters") or (),
            safe=safe_chars,
        )

    # Multi-value headers need explicit activation on ALB
    if "multiValueHeaders" in event:
        # may be None when testing on console
        headers = event["multiValueHeaders"] or {}
        environ["apig_wsgi.multi_value_headers"] = True
    else:
        # may be None when testing on console
        single_headers = event.get("headers") or {}
        headers = {key: [value] for key, value in single_headers.items()}
    for key, values in headers.items():
        key = key.upper().replace("-", "_")

        if key == "CONTENT_TYPE":
            environ["CONTENT_TYPE"] = values[-1]
        elif key == "HOST":
            environ["SERVER_NAME"] = values[-1]
        elif key == "X_FORWARDED_FOR":
            environ["REMOTE_ADDR"] = values[-1].split(", ")[0]
        elif key == "X_FORWARDED_PROTO":
            environ["wsgi.url_scheme"] = values[-1]
        elif key == "X_FORWARDED_PORT":
            environ["SERVER_PORT"] = values[-1]

        # Multi-value headers accumulate with ","
        environ["HTTP_" + key] = ",".join(values)

    if "requestContext" in event:
        environ["apig_wsgi.request_context"] = event["requestContext"]
    environ["apig_wsgi.full_event"] = event
    environ["apig_wsgi.context"] = context

    return environ


def get_environ_v2(event: dict[str, Any], context: Any) -> dict[str, Any]:
    body = get_body(event)
    headers = event["headers"]
    http = event["requestContext"]["http"]

    environ: dict[str, Any] = {
        "CONTENT_LENGTH": str(len(body)),
        "HTTP": "on",
        "HTTP_COOKIE": ";".join(event.get("cookies", ())),
        "PATH_INFO": urllib.parse.unquote(event["rawPath"], encoding="iso-8859-1"),
        "QUERY_STRING": event["rawQueryString"],
        "REMOTE_ADDR": http["sourceIp"],
        "REQUEST_METHOD": http["method"],
        "SCRIPT_NAME": "",
        "SERVER_NAME": "",
        "SERVER_PORT": "",
        "SERVER_PROTOCOL": http["protocol"],
        "wsgi.errors": sys.stderr,
        "wsgi.input": BytesIO(body),
        "wsgi.multiprocess": False,
        "wsgi.multithread": False,
        "wsgi.run_once": False,
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        # For backwards compatibility with apps upgrading from v1
        "apig_wsgi.multi_value_headers": False,
    }

    for key, raw_value in headers.items():
        key = key.upper().replace("-", "_")
        if key == "CONTENT_TYPE":
            environ["CONTENT_TYPE"] = raw_value.split(",")[-1]
        elif key == "HOST":
            environ["SERVER_NAME"] = raw_value.split(",")[-1]
        elif key == "X_FORWARDED_PROTO":
            environ["wsgi.url_scheme"] = raw_value.split(",")[-1]
        elif key == "X_FORWARDED_PORT":
            environ["SERVER_PORT"] = raw_value.split(",")[-1]
        elif key == "COOKIE":
            environ["HTTP_COOKIE"] += ";" + raw_value
            continue

        environ["HTTP_" + key] = raw_value

    environ["apig_wsgi.request_context"] = event["requestContext"]
    environ["apig_wsgi.full_event"] = event
    environ["apig_wsgi.context"] = context

    return environ


def get_body(event: dict[str, Any]) -> bytes:
    body: str = event.get("body", "") or ""
    if event.get("isBase64Encoded", False):
        return b64decode(body)
    return body.encode()


class BaseResponse:
    def __init__(
        self,
        *,
        binary_support: bool,
        non_binary_content_type_prefixes: tuple[str, ...],
    ) -> None:
        self.status_code = 500
        self.headers: list[tuple[str, str]] = []
        self.body = BytesIO()
        self.binary_support = binary_support
        self.non_binary_content_type_prefixes = non_binary_content_type_prefixes

    def start_response(
        self,
        status: str,
        response_headers: Sequence[tuple[str, str]],
        exc_info: _ExcInfoType = None,
    ) -> Callable[[bytes], int]:
        if exc_info is not None and exc_info[0] is not None:
            raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
        self.status_code = int(status.split()[0])
        self.headers.extend(response_headers)
        return self.body.write

    def consume(self, result: Iterable[bytes]) -> None:
        try:
            for data in result:
                if data:
                    self.body.write(data)
        finally:
            close = getattr(result, "close", None)
            if close:
                close()

    def _should_send_binary(self) -> bool:
        """
        Determines if binary response should be sent to API Gateway
        """
        if not self.binary_support:
            return False

        if self._get_content_encoding() > "":
            return True

        content_type = self._get_content_type()
        return not content_type.startswith(self.non_binary_content_type_prefixes)

    def _get_content_encoding(self) -> str:
        return self._get_header("content-encoding") or ""

    def _get_content_type(self) -> str:
        return self._get_header("content-type") or ""

    def _get_header(self, header_name: str) -> str | None:
        header_name = header_name.lower()
        matching_headers = [v for k, v in self.headers if k.lower() == header_name]
        if len(matching_headers):
            return matching_headers[-1]
        return None

    def as_apig_response(self) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError("Need to use subclass")


class V1Response(BaseResponse):
    def __init__(self, *, multi_value_headers: bool, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.multi_value_headers = multi_value_headers

    def as_apig_response(self) -> dict[str, Any]:
        response: dict[str, Any] = {"statusCode": self.status_code}
        # Return multiValueHeaders as header if support is required
        if self.multi_value_headers:
            headers = defaultdict(list)
            for k, v in self.headers:
                headers[k].append(v)
            response["multiValueHeaders"] = dict(headers)
        else:
            response["headers"] = dict(self.headers)

        if self._should_send_binary():
            response["isBase64Encoded"] = True
            response["body"] = b64encode(self.body.getvalue()).decode("utf-8")
        else:
            response["isBase64Encoded"] = False
            response["body"] = self.body.getvalue().decode("utf-8")

        return response


class V2Response(BaseResponse):
    def as_apig_response(self) -> dict[str, Any]:
        response: dict[str, Any] = {
            "statusCode": self.status_code,
        }

        headers = {}
        cookies = []
        for key, value in self.headers:
            key_lower = key.lower()
            if key_lower == "set-cookie":
                cookies.append(value)
            else:
                headers[key_lower] = value

        response["cookies"] = cookies
        response["headers"] = headers

        if self._should_send_binary():
            response["isBase64Encoded"] = True
            response["body"] = b64encode(self.body.getvalue()).decode("utf-8")
        else:
            response["isBase64Encoded"] = False
            response["body"] = self.body.getvalue().decode("utf-8")

        return response
