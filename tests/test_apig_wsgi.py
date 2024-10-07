from __future__ import annotations

import sys
from base64 import b64encode
from collections.abc import Generator
from collections.abc import Iterable
from io import BytesIO
from typing import Any
from typing import Callable

import pytest

from apig_wsgi import _ExcInfoType
from apig_wsgi import make_lambda_handler


class App:
    def __init__(
        self,
        headers: list[tuple[str, str]],
        response: bytes,
        exc_info: _ExcInfoType,
    ) -> None:
        self.headers = headers
        self.response = response
        self.exc_info = exc_info
        self.handler = make_lambda_handler(self)

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: Callable[
            [
                str,
                list[tuple[str, str]],
                _ExcInfoType,
            ],
            Callable[[bytes], Any],
        ],
    ) -> Iterable[bytes]:
        self.environ = environ
        start_response("200 OK", self.headers, self.exc_info)
        return BytesIO(self.response)


@pytest.fixture()
def simple_app() -> Generator[App]:
    yield App(
        headers=[("Content-Type", "text/plain")],
        response=b"Hello World\n",
        exc_info=None,
    )


parametrize_default_text_content_type = pytest.mark.parametrize(
    "text_content_type",
    [
        "text/plain",
        "text/html",
        "application/json",
        "application/problem+json",
        "application/vnd.api+json",
    ],
)


CUSTOM_NON_BINARY_CONTENT_TYPE_PREFIXES = ["test/custom", "application/vnd.custom"]

parametrize_custom_text_content_type = pytest.mark.parametrize(
    "text_content_type", CUSTOM_NON_BINARY_CONTENT_TYPE_PREFIXES
)


class ContextStub:
    """
    Stub for context object as documented at
    https://docs.aws.amazon.com/lambda/latest/dg/python-context.html
    """

    def __init__(
        self,
        function_name: str = "app",
        function_version: str = "$LATEST",
        invoked_function_arn: str = "arn:test:lambda:us-east-1:0123456789:function:app",
        memory_limit_in_mb: int = 128,
        aws_request_id: str | None = None,
        log_stream_name: str = "app-group",
        log_group_name: str = "app-stream",
    ) -> None:
        self.function_name = function_name
        self.function_version = function_version
        self.invoked_function_arn = invoked_function_arn
        self.memory_limit_in_mb = memory_limit_in_mb
        self.aws_request_id = aws_request_id
        self.log_group_name = log_group_name
        self.log_stream_name = log_stream_name


# v1 tests


class Sentinel:
    pass


SENTINEL = Sentinel()


def make_v1_event(
    *,
    method: str = "GET",
    path: str = "/",
    qs_params: dict[str, list[str]] | None = None,
    qs_params_multi: bool = True,
    headers: dict[str, list[str]] | None = None,
    headers_multi: bool = True,
    body: str = "",
    binary: bool = False,
    request_context: dict[str, Any] | None | Sentinel = SENTINEL,
) -> dict[str, Any]:
    if headers is None:
        headers = {"Host": ["example.com"]}

    event: dict[str, Any] = {
        "version": "1.0",
        "httpMethod": method,
        "path": path,
    }

    if qs_params_multi:
        event["multiValueQueryStringParameters"] = qs_params
    else:
        if qs_params is None:
            event["queryStringParameters"] = None
        else:
            event["queryStringParameters"] = {
                key: values[-1] for key, values in qs_params.items()
            }

    if headers_multi:
        event["multiValueHeaders"] = headers
    else:
        event["headers"] = {key: values[-1] for key, values in headers.items()}

    if binary:
        event["body"] = b64encode(body.encode("utf-8"))
        event["isBase64Encoded"] = True
    else:
        event["body"] = body
        event["isBase64Encoded"] = False

    if request_context is not SENTINEL:
        event["requestContext"] = request_context

    return event


class TestV1Events:
    def test_get(self, simple_app: App) -> None:
        response = simple_app.handler(make_v1_event(), None)

        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {"Content-Type": ["text/plain"]},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_get_missing_content_type(self, simple_app: App) -> None:
        simple_app.headers = []

        response = simple_app.handler(make_v1_event(), None)

        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_get_single_header(self, simple_app: App) -> None:
        response = simple_app.handler(make_v1_event(headers_multi=False), None)

        assert response == {
            "statusCode": 200,
            "headers": {"Content-Type": "text/plain"},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    @parametrize_default_text_content_type
    def test_get_binary_support_default_text_content_types(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = [("Content-Type", text_content_type)]

        response = simple_app.handler(make_v1_event(), None)
        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {"Content-Type": [text_content_type]},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    @parametrize_default_text_content_type
    def test_get_binary_support_default_text_content_types_encoded(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = [
            ("Content-Type", text_content_type),
            ("Content-Encoding", "brotli"),
        ]

        response = simple_app.handler(make_v1_event(), None)
        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {
                "Content-Type": [text_content_type],
                "Content-Encoding": ["brotli"],
            },
            "isBase64Encoded": True,
            "body": b64encode(b"Hello World\n").decode("utf-8"),
        }

    @parametrize_custom_text_content_type
    def test_get_binary_support_custom_text_content_types(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(
            simple_app,
            binary_support=True,
            non_binary_content_type_prefixes=CUSTOM_NON_BINARY_CONTENT_TYPE_PREFIXES,
        )
        simple_app.headers = [("Content-Type", text_content_type)]

        response = simple_app.handler(make_v1_event(), None)
        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {"Content-Type": [text_content_type]},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_get_binary_support_binary(self, simple_app: App) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = [("Content-Type", "application/octet-stream")]
        simple_app.response = b"\x13\x37"

        response = simple_app.handler(make_v1_event(), None)

        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {"Content-Type": ["application/octet-stream"]},
            "isBase64Encoded": True,
            "body": b64encode(b"\x13\x37").decode("utf-8"),
        }

    def test_get_binary_support_alb_default(self, simple_app: App) -> None:
        simple_app.handler = make_lambda_handler(simple_app)
        simple_app.headers = [("Content-Type", "application/octet-stream")]
        simple_app.response = b"\x13\x37"

        response = simple_app.handler(make_alb_event(), None)

        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {"Content-Type": ["application/octet-stream"]},
            "isBase64Encoded": True,
            "body": b64encode(b"\x13\x37").decode("utf-8"),
        }

    def test_get_binary_support_alb_enabled(self, simple_app: App) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = [("Content-Type", "application/octet-stream")]
        simple_app.response = b"\x13\x37"

        response = simple_app.handler(make_alb_event(), None)

        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {"Content-Type": ["application/octet-stream"]},
            "isBase64Encoded": True,
            "body": b64encode(b"\x13\x37").decode("utf-8"),
        }

    @parametrize_default_text_content_type
    def test_get_binary_support_binary_default_text_with_gzip_content_encoding(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = [
            ("Content-Type", text_content_type),
            ("Content-Encoding", "gzip"),
        ]
        simple_app.response = b"\x13\x37"

        response = simple_app.handler(make_v1_event(), None)

        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {
                "Content-Type": [text_content_type],
                "Content-Encoding": ["gzip"],
            },
            "isBase64Encoded": True,
            "body": b64encode(b"\x13\x37").decode("utf-8"),
        }

    @parametrize_custom_text_content_type
    def test_get_binary_support_binary_custom_text_with_gzip_content_encoding(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(
            simple_app,
            binary_support=True,
            non_binary_content_type_prefixes=CUSTOM_NON_BINARY_CONTENT_TYPE_PREFIXES,
        )
        simple_app.headers = [
            ("Content-Type", text_content_type),
            ("Content-Encoding", "gzip"),
        ]
        simple_app.response = b"\x13\x37"

        response = simple_app.handler(make_v1_event(), None)

        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {
                "Content-Type": [text_content_type],
                "Content-Encoding": ["gzip"],
            },
            "isBase64Encoded": True,
            "body": b64encode(b"\x13\x37").decode("utf-8"),
        }

    def test_get_binary_support_no_content_type(self, simple_app: App) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = []
        simple_app.response = b"\x13\x37"

        response = simple_app.handler(make_v1_event(), None)

        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {},
            "isBase64Encoded": True,
            "body": b64encode(b"\x13\x37").decode("utf-8"),
        }

    def test_post(self, simple_app: App) -> None:
        event = make_v1_event(method="POST", body="The World is Large")

        response = simple_app.handler(event, None)

        assert simple_app.environ["wsgi.input"].read() == b"The World is Large"
        assert simple_app.environ["CONTENT_LENGTH"] == str(len(b"The World is Large"))
        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {"Content-Type": ["text/plain"]},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_post_binary_support(self, simple_app: App) -> None:
        event = make_v1_event(method="POST", body="dogfood", binary=True)

        response = simple_app.handler(event, None)

        assert simple_app.environ["wsgi.input"].read() == b"dogfood"
        assert simple_app.environ["CONTENT_LENGTH"] == str(len(b"dogfood"))
        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {"Content-Type": ["text/plain"]},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_path_unquoting(self, simple_app: App) -> None:
        event = make_v1_event(path="/api/path%2Finfo")

        simple_app.handler(event, None)

        assert simple_app.environ["PATH_INFO"] == "/api/path/info"

    def test_querystring_none(self, simple_app: App) -> None:
        event = make_v1_event()

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == ""

    def test_querystring_none_single(self, simple_app: App) -> None:
        event = make_v1_event(qs_params_multi=False)

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == ""

    def test_querystring_empty(self, simple_app: App) -> None:
        event = make_v1_event(qs_params={})

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == ""

    def test_querystring_empty_single(self, simple_app: App) -> None:
        event = make_v1_event(qs_params={}, qs_params_multi=False)

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == ""

    def test_querystring_one(self, simple_app: App) -> None:
        event = make_v1_event(qs_params={"foo": ["bar"]})

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "foo=bar"

    def test_querystring_one_single(self, simple_app: App) -> None:
        event = make_v1_event(qs_params={"foo": ["bar"]}, qs_params_multi=False)

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "foo=bar"

    def test_querystring_encoding_plus_value(self, simple_app: App) -> None:
        event = make_v1_event(qs_params={"a": ["b+c"]}, qs_params_multi=False)

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a=b%2Bc"

    def test_querystring_encoding_plus_key(self, simple_app: App) -> None:
        event = make_v1_event(qs_params={"a+b": ["c"]}, qs_params_multi=False)

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a%2Bb=c"

    def test_querystring_multi(self, simple_app: App) -> None:
        event = make_v1_event(qs_params={"foo": ["bar", "baz"]})

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "foo=bar&foo=baz"

    def test_querystring_multi_encoding_plus_value(self, simple_app: App) -> None:
        event = make_v1_event(qs_params={"a": ["b+c", "d"]})

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a=b%2Bc&a=d"

    def test_querystring_multi_encoding_plus_key(self, simple_app: App) -> None:
        event = make_v1_event(qs_params={"a+b": ["c"]})

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a%2Bb=c"

    def test_plain_header(self, simple_app: App) -> None:
        event = make_v1_event(headers={"Test-Header": ["foobar"]})

        simple_app.handler(event, None)

        assert simple_app.environ["HTTP_TEST_HEADER"] == "foobar"

    def test_plain_header_single(self, simple_app: App) -> None:
        event = make_v1_event(headers={"Test-Header": ["foobar"]}, headers_multi=False)

        simple_app.handler(event, None)

        assert simple_app.environ["HTTP_TEST_HEADER"] == "foobar"

    def test_plain_header_multi(self, simple_app: App) -> None:
        event = make_v1_event(headers={"Test-Header": ["foo", "bar"]})

        simple_app.handler(event, None)

        assert simple_app.environ["HTTP_TEST_HEADER"] == "foo,bar"

    def test_special_headers(self, simple_app: App) -> None:
        event = make_v1_event(
            headers={
                "Content-Type": ["text/plain"],
                "Host": ["example.com"],
                "X-Forwarded-For": ["1.2.3.4, 5.6.7.8"],
                "X-Forwarded-Proto": ["https"],
                "X-Forwarded-Port": ["123"],
            }
        )

        simple_app.handler(event, None)

        assert simple_app.environ["CONTENT_TYPE"] == "text/plain"
        assert simple_app.environ["HTTP_CONTENT_TYPE"] == "text/plain"
        assert simple_app.environ["SERVER_NAME"] == "example.com"
        assert simple_app.environ["HTTP_HOST"] == "example.com"
        assert simple_app.environ["REMOTE_ADDR"] == "1.2.3.4"
        assert simple_app.environ["HTTP_X_FORWARDED_FOR"] == "1.2.3.4, 5.6.7.8"
        assert simple_app.environ["wsgi.url_scheme"] == "https"
        assert simple_app.environ["HTTP_X_FORWARDED_PROTO"] == "https"
        assert simple_app.environ["SERVER_PORT"] == "123"
        assert simple_app.environ["HTTP_X_FORWARDED_PORT"] == "123"

    def test_special_content_type(self, simple_app: App) -> None:
        event = make_v1_event(headers={"Content-Type": ["text/plain"]})

        simple_app.handler(event, None)

        assert simple_app.environ["CONTENT_TYPE"] == "text/plain"
        assert simple_app.environ["HTTP_CONTENT_TYPE"] == "text/plain"

    def test_special_host(self, simple_app: App) -> None:
        event = make_v1_event(headers={"Host": ["example.com"]})

        simple_app.handler(event, None)

        assert simple_app.environ["SERVER_NAME"] == "example.com"
        assert simple_app.environ["HTTP_HOST"] == "example.com"

    def test_special_x_forwarded_for(self, simple_app: App) -> None:
        event = make_v1_event(headers={"X-Forwarded-For": ["1.2.3.4, 5.6.7.8"]})

        simple_app.handler(event, None)

        assert simple_app.environ["REMOTE_ADDR"] == "1.2.3.4"
        assert simple_app.environ["HTTP_X_FORWARDED_FOR"] == "1.2.3.4, 5.6.7.8"

    def test_x_forwarded_proto(self, simple_app: App) -> None:
        event = make_v1_event(headers={"X-Forwarded-Proto": ["https"]})

        simple_app.handler(event, None)

        assert simple_app.environ["wsgi.url_scheme"] == "https"
        assert simple_app.environ["HTTP_X_FORWARDED_PROTO"] == "https"

    def test_x_forwarded_port(self, simple_app: App) -> None:
        event = make_v1_event(headers={"X-Forwarded-Port": ["123"]})

        simple_app.handler(event, None)

        assert simple_app.environ["SERVER_PORT"] == "123"
        assert simple_app.environ["HTTP_X_FORWARDED_PORT"] == "123"

    def test_no_headers(self, simple_app: App) -> None:
        # allow headers to be missing from event
        event = make_v1_event()
        del event["multiValueHeaders"]

        simple_app.handler(event, None)

    def test_headers_None(self, simple_app: App) -> None:
        # allow headers to be 'None' from APIG test console
        event = make_v1_event()
        event["multiValueHeaders"] = None

        simple_app.handler(event, None)

    def test_exc_info(self, simple_app: App) -> None:
        try:
            raise ValueError("Example exception")
        except ValueError:
            simple_app.exc_info = sys.exc_info()

        with pytest.raises(ValueError) as excinfo:
            simple_app.handler(make_v1_event(), None)

        assert str(excinfo.value) == "Example exception"

    def test_request_context(self, simple_app: App) -> None:
        context = {"authorizer": {"user": "test@example.com"}}
        event = make_v1_event(request_context=context)

        simple_app.handler(event, None)

        assert simple_app.environ["apig_wsgi.request_context"] == context

    def test_request_context_none(self, simple_app: App) -> None:
        # Invoking lambdas can lead to requestContext being JSON null
        event = make_v1_event(request_context=None)

        simple_app.handler(event, None)

        # Simply don't crash

    def test_full_event(self, simple_app: App) -> None:
        event = make_v1_event()

        simple_app.handler(event, None)

        assert simple_app.environ["apig_wsgi.full_event"] == event

    def test_elb_health_check(self, simple_app: App) -> None:
        """
        Check compatibility with health check events as per:
        https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html#enable-health-checks-lambda  # noqa: E501
        """
        event = {
            "requestContext": {"elb": {"targetGroupArn": "..."}},
            "httpMethod": "GET",
            "path": "/",
            "queryStringParameters": {},
            "multiValueHeaders": {"user-agent": ["ELB-HealthChecker/2.0"]},
            "body": "",
            "isBase64Encoded": False,
        }

        simple_app.handler(event, None)

        environ = simple_app.environ
        assert environ["SERVER_NAME"] == ""
        assert environ["SERVER_PORT"] == ""
        assert environ["wsgi.url_scheme"] == "http"

    def test_context(self, simple_app: App) -> None:
        context = ContextStub(aws_request_id="test-request-id")

        simple_app.handler(make_v1_event(), context)

        assert simple_app.environ["apig_wsgi.context"] == context

    def test_empty_and_uncloseable_content(self) -> None:
        def app(environ, start_response):
            start_response("200 OK", [], None)
            return [b"Hi", b"", b" there!", b""]

        handler = make_lambda_handler(app)
        event = make_v1_event()

        response = handler(event, None)

        assert response["body"] == "Hi there!"


# ALB tests


def make_alb_event(**kwargs: Any) -> dict[str, Any]:
    event = make_v1_event(
        request_context={
            "elb": {"targetGroupArn": "arn:aws:elasticloadbalancing:::targetgroup/etc"}
        },
        **kwargs,
    )

    del event["version"]

    return event


class TestAlbEvents:
    # Query string params from ALB are the same as rawQueryStringParameters
    # in API GW V2... that is they don't need to be encoded.
    def test_querystring_encoding_plus_value(self, simple_app: App) -> None:
        event = make_alb_event(qs_params={"a": ["b+c"]}, qs_params_multi=False)

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a=b+c"

    def test_querystring_encoding_plus_key(self, simple_app: App) -> None:
        event = make_alb_event(qs_params={"a+b": ["c"]}, qs_params_multi=False)

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a+b=c"

    def test_querystring_multi(self, simple_app: App) -> None:
        event = make_alb_event(qs_params={"foo": ["bar", "baz"]})

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "foo=bar&foo=baz"

    def test_querystring_multi_encoding_plus_value(self, simple_app: App) -> None:
        event = make_alb_event(qs_params={"a": ["b+c", "d"]})

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a=b+c&a=d"

    def test_querystring_multi_encoding_plus_key(self, simple_app: App) -> None:
        event = make_alb_event(qs_params={"a+b": ["c"]})

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a+b=c"

    def test_querystring_contains_encoded_value(self, simple_app: App) -> None:
        event = make_alb_event(qs_params={"a": ["foo%3Dbar"]}, qs_params_multi=False)

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a=foo%3Dbar"

    def test_querystring_multi_contains_encoded_value(self, simple_app: App) -> None:
        # a = ['foo=bar', '$20', '100%']
        event = make_alb_event(
            qs_params={"a": ["foo%3Dbar", "%2420", "100%25"]}, qs_params_multi=True
        )

        simple_app.handler(event, None)

        assert simple_app.environ["QUERY_STRING"] == "a=foo%3Dbar&a=%2420&a=100%25"


# v2 tests


def make_v2_event(
    *,
    host: str = "example.com",
    method: str = "GET",
    path: str = "/",
    query_string: str | None = None,
    cookies: list[str] | None = None,
    headers: dict[str, str] | None = None,
    body: str = "",
    binary: bool = False,
) -> dict[str, Any]:
    if cookies is None:
        cookies = []
    if headers is None:
        headers = {"Host": "example.com"}

    event: dict[str, Any] = {
        "version": "2.0",
        "rawQueryString": query_string,
        "rawPath": path,
        "headers": headers,
        "cookies": cookies,
        "requestContext": {
            "http": {
                "method": method,
                "path": path.rstrip("/"),
                "sourceIp": "1.2.3.4",
                "protocol": "https",
            },
        },
    }

    if binary:
        event["body"] = b64encode(body.encode())
        event["isBase64Encoded"] = True
    else:
        event["body"] = body
        event["isBase64Encoded"] = False

    return event


class TestV2Events:
    def test_get(self, simple_app: App) -> None:
        response = simple_app.handler(make_v2_event(), None)

        assert response == {
            "statusCode": 200,
            "cookies": [],
            "headers": {"content-type": "text/plain"},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_get_missing_content_type(self, simple_app: App) -> None:
        simple_app.headers = []

        response = simple_app.handler(make_v2_event(), None)

        assert response == {
            "statusCode": 200,
            "cookies": [],
            "headers": {},
            "isBase64Encoded": True,
            "body": "SGVsbG8gV29ybGQK",
        }

    def test_cookie(self, simple_app: App) -> None:
        simple_app.handler(make_v2_event(cookies=["testcookie=abc"]), None)

        assert simple_app.environ["HTTP_COOKIE"] == "testcookie=abc"

    def test_two_cookies(self, simple_app: App) -> None:
        simple_app.handler(
            make_v2_event(cookies=["testcookie=abc", "testcookie2=def"]), None
        )

        assert simple_app.environ["HTTP_COOKIE"] == "testcookie=abc;testcookie2=def"

    def test_mixed_cookies(self, simple_app: App) -> None:
        """
        Check that if, somehow, API Gateway leaves a cookie as a "cookie"
        header, we combine that with the 'cookies' key. The API Gateway
        documentation doesn't directly specify that it always parses out all
        Cookie headers, so this is a defence against this possible behaviour.
        """
        simple_app.handler(
            make_v2_event(
                cookies=["testcookie=abc"],
                headers={"Content-Type": "text/plain", "Cookie": "testcookie2=def"},
            ),
            None,
        )

        assert simple_app.environ["HTTP_COOKIE"] == "testcookie=abc;testcookie2=def"

    def test_set_one_cookie(self, simple_app: App) -> None:
        simple_app.headers = [
            ("Content-Type", "text/plain"),
            ("Set-Cookie", "testcookie=1; Path=/; SameSite=strict"),
        ]
        response = simple_app.handler(make_v2_event(), None)

        assert response == {
            "statusCode": 200,
            "cookies": ["testcookie=1; Path=/; SameSite=strict"],
            "headers": {"content-type": "text/plain"},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_set_two_cookies(self, simple_app: App) -> None:
        simple_app.headers = [
            ("Content-Type", "text/plain"),
            ("Set-Cookie", "testcookie=abc; Path=/; SameSite=strict"),
            ("Set-Cookie", "testcookie2=def; Path=/; SameSite=strict"),
        ]
        response = simple_app.handler(make_v2_event(), None)

        assert response == {
            "statusCode": 200,
            "cookies": [
                "testcookie=abc; Path=/; SameSite=strict",
                "testcookie2=def; Path=/; SameSite=strict",
            ],
            "headers": {"content-type": "text/plain"},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    @parametrize_default_text_content_type
    def test_get_binary_support_default_text_content_types(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = [("Content-Type", text_content_type)]

        response = simple_app.handler(make_v2_event(), None)
        assert response == {
            "statusCode": 200,
            "cookies": [],
            "headers": {"content-type": text_content_type},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    @parametrize_default_text_content_type
    def test_get_binary_support_default_text_content_types_encoded(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = [
            ("Content-Type", text_content_type),
            ("Content-Encoding", "brotli"),
        ]

        response = simple_app.handler(make_v1_event(), None)
        assert response == {
            "statusCode": 200,
            "multiValueHeaders": {
                "Content-Type": [text_content_type],
                "Content-Encoding": ["brotli"],
            },
            "isBase64Encoded": True,
            "body": b64encode(b"Hello World\n").decode("utf-8"),
        }

    @parametrize_custom_text_content_type
    def test_get_binary_support_custom_text_content_types(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(
            simple_app,
            binary_support=True,
            non_binary_content_type_prefixes=CUSTOM_NON_BINARY_CONTENT_TYPE_PREFIXES,
        )
        simple_app.headers = [("Content-Type", text_content_type)]

        response = simple_app.handler(make_v2_event(), None)
        assert response == {
            "statusCode": 200,
            "cookies": [],
            "headers": {"content-type": text_content_type},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_get_binary_support_binary(self, simple_app: App) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = [("Content-Type", "application/octet-stream")]
        simple_app.response = b"\x13\x37"

        response = simple_app.handler(make_v2_event(), None)

        assert response == {
            "statusCode": 200,
            "cookies": [],
            "headers": {"content-type": "application/octet-stream"},
            "isBase64Encoded": True,
            "body": b64encode(b"\x13\x37").decode("utf-8"),
        }

    @parametrize_default_text_content_type
    def test_get_binary_support_binary_default_text_with_gzip_content_encoding(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
        simple_app.headers = [
            ("Content-Type", text_content_type),
            ("Content-Encoding", "gzip"),
        ]
        simple_app.response = b"\x13\x37"

        response = simple_app.handler(make_v2_event(), None)

        assert response == {
            "statusCode": 200,
            "cookies": [],
            "headers": {
                "content-type": text_content_type,
                "content-encoding": "gzip",
            },
            "isBase64Encoded": True,
            "body": b64encode(b"\x13\x37").decode("utf-8"),
        }

    @parametrize_custom_text_content_type
    def test_get_binary_support_binary_custom_text_with_gzip_content_encoding(
        self, simple_app: App, text_content_type: str
    ) -> None:
        simple_app.handler = make_lambda_handler(
            simple_app,
            binary_support=True,
            non_binary_content_type_prefixes=CUSTOM_NON_BINARY_CONTENT_TYPE_PREFIXES,
        )
        simple_app.headers = [
            ("Content-Type", text_content_type),
            ("Content-Encoding", "gzip"),
        ]
        simple_app.response = b"\x13\x37"

        response = simple_app.handler(make_v2_event(), None)

        assert response == {
            "statusCode": 200,
            "cookies": [],
            "headers": {
                "content-type": text_content_type,
                "content-encoding": "gzip",
            },
            "isBase64Encoded": True,
            "body": b64encode(b"\x13\x37").decode("utf-8"),
        }

    def test_plain_header(self, simple_app: App) -> None:
        event = make_v2_event(headers={"Test-Header": "foo"})

        simple_app.handler(event, None)

        assert simple_app.environ["HTTP_TEST_HEADER"] == "foo"

    def test_special_headers(self, simple_app: App) -> None:
        event = make_v2_event(
            headers={
                "Content-Type": "text/plain",
                "Host": "example.com",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Port": "123",
            }
        )

        simple_app.handler(event, None)

        assert simple_app.environ["CONTENT_TYPE"] == "text/plain"
        assert simple_app.environ["HTTP_CONTENT_TYPE"] == "text/plain"
        assert simple_app.environ["SERVER_NAME"] == "example.com"
        assert simple_app.environ["HTTP_HOST"] == "example.com"
        assert simple_app.environ["wsgi.url_scheme"] == "https"
        assert simple_app.environ["HTTP_X_FORWARDED_PROTO"] == "https"
        assert simple_app.environ["SERVER_PORT"] == "123"
        assert simple_app.environ["HTTP_X_FORWARDED_PORT"] == "123"

    def test_post(self, simple_app: App) -> None:
        event = make_v2_event(method="POST", body="The World is Large")

        response = simple_app.handler(event, None)

        assert simple_app.environ["wsgi.input"].read() == b"The World is Large"
        assert simple_app.environ["CONTENT_LENGTH"] == str(len(b"The World is Large"))
        assert response == {
            "statusCode": 200,
            "cookies": [],
            "headers": {"content-type": "text/plain"},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_post_binary_support(self, simple_app: App) -> None:
        event = make_v2_event(method="POST", body="dogfood", binary=True)

        response = simple_app.handler(event, None)

        assert simple_app.environ["wsgi.input"].read() == b"dogfood"
        assert simple_app.environ["CONTENT_LENGTH"] == str(len(b"dogfood"))
        assert response == {
            "statusCode": 200,
            "cookies": [],
            "headers": {"content-type": "text/plain"},
            "isBase64Encoded": False,
            "body": "Hello World\n",
        }

    def test_path_unquoting(self, simple_app: App) -> None:
        event = make_v2_event(path="/api/path%2Finfo")

        simple_app.handler(event, None)

        assert simple_app.environ["PATH_INFO"] == "/api/path/info"

    def test_empty_and_uncloseable_content(self) -> None:
        def app(environ, start_response):
            start_response("200 OK", [], None)
            return [b"Hi", b"", b" there!", b""]

        handler = make_lambda_handler(app)
        event = make_v2_event()

        response = handler(event, None)

        assert response["body"] == b64encode(b"Hi there!").decode("utf-8")


# unknown version test


class TestUnknownVersionEvents:
    def test_errors(self, simple_app: App) -> None:
        with pytest.raises(ValueError) as excinfo:
            simple_app.handler({"version": "distant-future"}, None)

        assert str(excinfo.value) == "Unknown version 'distant-future'"
