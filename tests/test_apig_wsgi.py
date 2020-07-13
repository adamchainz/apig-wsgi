import sys
from base64 import b64encode
from io import BytesIO

import pytest

from apig_wsgi import make_lambda_handler

CUSTOM_NON_BINARY_CONTENT_TYPE_PREFIXES = ["test/custom", "application/vnd.custom"]


@pytest.fixture()
def simple_app():
    def app(environ, start_response):
        app.environ = environ
        start_response("200 OK", app.headers, app.exc_info)
        return BytesIO(app.response)

    app.headers = [("Content-Type", "text/plain")]
    app.response = b"Hello World\n"
    app.handler = make_lambda_handler(app)
    app.exc_info = None
    yield app


parametrize_default_text_content_type = pytest.mark.parametrize(
    "text_content_type",
    ["text/plain", "text/html", "application/json", "application/vnd.api+json"],
)


parametrize_custom_text_content_type = pytest.mark.parametrize(
    "text_content_type", CUSTOM_NON_BINARY_CONTENT_TYPE_PREFIXES
)


def make_event(
    method="GET",
    qs_params=None,
    qs_params_multi=True,
    headers=None,
    headers_multi=True,
    body="",
    binary=False,
    request_context=None,
):
    if headers is None:
        headers = {"Host": ["example.com"]}

    event = {
        "httpMethod": method,
        "path": "/",
        "multiValueHeaders": headers,
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

    if request_context is not None:
        event["requestContext"] = request_context

    return event


class ContextStub:
    def __init__(
        self,
        function_name="app",
        function_version="$LATEST",
        invoked_function_arn="arn:test:lambda:us-east-1:0123456789:function:app",
        memory_limit_in_mb=128,
        aws_request_id=None,
        log_stream_name="app-group",
        log_group_name="app-stream",
        identity=None,
        client_context=None,
        remaining_time_in_millis=60,
    ):
        self.function_name = function_name
        self.function_version = function_version
        self.invoked_function_arn = invoked_function_arn
        self.memory_limit_in_mb = memory_limit_in_mb
        self.aws_request_id = aws_request_id
        self.log_group_name = log_group_name
        self.log_stream_name = log_stream_name
        if identity:
            self.identity = identity
        if client_context:
            self.client_context = client_context
        self._remaining_time_in_millis = remaining_time_in_millis


def test_get(simple_app):
    response = simple_app.handler(make_event(), None)

    assert response == {
        "statusCode": 200,
        "headers": {"Content-Type": "text/plain"},
        "body": "Hello World\n",
    }


def test_get_missing_content_type(simple_app):
    simple_app.headers = []

    response = simple_app.handler(make_event(), None)

    assert response == {"statusCode": 200, "headers": {}, "body": "Hello World\n"}


@parametrize_default_text_content_type
def test_get_binary_support_default_text_content_types(simple_app, text_content_type):
    simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
    simple_app.headers = [("Content-Type", text_content_type)]

    response = simple_app.handler(make_event(), None)
    assert response == {
        "statusCode": 200,
        "headers": {"Content-Type": text_content_type},
        "body": "Hello World\n",
    }


@parametrize_custom_text_content_type
def test_get_binary_support_custom_text_content_types(simple_app, text_content_type):
    simple_app.handler = make_lambda_handler(
        simple_app,
        binary_support=True,
        non_binary_content_type_prefixes=CUSTOM_NON_BINARY_CONTENT_TYPE_PREFIXES,
    )
    simple_app.headers = [("Content-Type", text_content_type)]

    response = simple_app.handler(make_event(), None)
    assert response == {
        "statusCode": 200,
        "headers": {"Content-Type": text_content_type},
        "body": "Hello World\n",
    }


def test_get_binary_support_binary(simple_app):
    simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
    simple_app.headers = [("Content-Type", "application/octet-stream")]
    simple_app.response = b"\x13\x37"

    response = simple_app.handler(make_event(), None)

    assert response == {
        "statusCode": 200,
        "headers": {"Content-Type": "application/octet-stream"},
        "body": b64encode(b"\x13\x37").decode("utf-8"),
        "isBase64Encoded": True,
    }


@parametrize_default_text_content_type
def test_get_binary_support_binary_default_text_with_gzip_content_encoding(
    simple_app, text_content_type
):
    simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
    simple_app.headers = [
        ("Content-Type", text_content_type),
        ("Content-Encoding", "gzip"),
    ]
    simple_app.response = b"\x13\x37"

    response = simple_app.handler(make_event(), None)

    assert response == {
        "statusCode": 200,
        "headers": {"Content-Type": text_content_type, "Content-Encoding": "gzip"},
        "body": b64encode(b"\x13\x37").decode("utf-8"),
        "isBase64Encoded": True,
    }


@parametrize_custom_text_content_type
def test_get_binary_support_binary_custom_text_with_gzip_content_encoding(
    simple_app, text_content_type
):
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

    response = simple_app.handler(make_event(), None)

    assert response == {
        "statusCode": 200,
        "headers": {"Content-Type": text_content_type, "Content-Encoding": "gzip"},
        "body": b64encode(b"\x13\x37").decode("utf-8"),
        "isBase64Encoded": True,
    }


def test_get_binary_support_no_content_type(simple_app):
    simple_app.handler = make_lambda_handler(simple_app, binary_support=True)
    simple_app.headers = []
    simple_app.response = b"\x13\x37"

    response = simple_app.handler(make_event(), None)

    assert response == {
        "statusCode": 200,
        "headers": {},
        "body": b64encode(b"\x13\x37").decode("utf-8"),
        "isBase64Encoded": True,
    }


def test_post(simple_app):
    event = make_event(method="POST", body="The World is Large")

    response = simple_app.handler(event, None)

    assert simple_app.environ["wsgi.input"].read() == b"The World is Large"
    assert simple_app.environ["CONTENT_LENGTH"] == str(len(b"The World is Large"))
    assert response == {
        "statusCode": 200,
        "headers": {"Content-Type": "text/plain"},
        "body": "Hello World\n",
    }


def test_post_binary_support(simple_app):
    simple_app.handler = make_lambda_handler(simple_app)
    event = make_event(method="POST", body="dogfood", binary=True)

    response = simple_app.handler(event, None)

    assert simple_app.environ["wsgi.input"].read() == b"dogfood"
    assert simple_app.environ["CONTENT_LENGTH"] == str(len(b"dogfood"))
    assert response == {
        "statusCode": 200,
        "headers": {"Content-Type": "text/plain"},
        "body": "Hello World\n",
    }


def test_querystring_none(simple_app):
    event = make_event()

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == ""


def test_querystring_none_single(simple_app):
    event = make_event(qs_params_multi=False)

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == ""


def test_querystring_empty(simple_app):
    event = make_event(qs_params={})

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == ""


def test_querystring_empty_single(simple_app):
    event = make_event(qs_params={}, qs_params_multi=False)

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == ""


def test_querystring_one(simple_app):
    event = make_event(qs_params={"foo": ["bar"]})

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == "foo=bar"


def test_querystring_one_single(simple_app):
    event = make_event(qs_params={"foo": ["bar"]}, qs_params_multi=False)

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == "foo=bar"


def test_querystring_encoding_value(simple_app):
    event = make_event(qs_params={"foo": ["a%20bar"]})

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == "foo=a%20bar"


def test_querystring_encoding_key(simple_app):
    event = make_event(qs_params={"a%20foo": ["bar"]})

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == "a%20foo=bar"


def test_querystring_multi(simple_app):
    event = make_event(qs_params={"foo": ["bar", "baz"]})

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == "foo=bar&foo=baz"


def test_plain_header(simple_app):
    event = make_event(headers={"Test-Header": ["foobar"]})

    simple_app.handler(event, None)

    assert simple_app.environ["HTTP_TEST_HEADER"] == "foobar"


def test_plain_header_single(simple_app):
    event = make_event(headers={"Test-Header": ["foobar"]}, headers_multi=False)

    simple_app.handler(event, None)

    assert simple_app.environ["HTTP_TEST_HEADER"] == "foobar"


def test_plain_header_multi(simple_app):
    event = make_event(headers={"Test-Header": ["foo", "bar"]})

    simple_app.handler(event, None)

    assert simple_app.environ["HTTP_TEST_HEADER"] == "foo,bar"


def test_special_headers(simple_app):
    event = make_event(
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


def test_special_content_type(simple_app):
    event = make_event(headers={"Content-Type": ["text/plain"]})

    simple_app.handler(event, None)

    assert simple_app.environ["CONTENT_TYPE"] == "text/plain"
    assert simple_app.environ["HTTP_CONTENT_TYPE"] == "text/plain"


def test_special_host(simple_app):
    event = make_event(headers={"Host": ["example.com"]})

    simple_app.handler(event, None)

    assert simple_app.environ["SERVER_NAME"] == "example.com"
    assert simple_app.environ["HTTP_HOST"] == "example.com"


def test_special_x_forwarded_for(simple_app):
    event = make_event(headers={"X-Forwarded-For": ["1.2.3.4, 5.6.7.8"]})

    simple_app.handler(event, None)

    assert simple_app.environ["REMOTE_ADDR"] == "1.2.3.4"
    assert simple_app.environ["HTTP_X_FORWARDED_FOR"] == "1.2.3.4, 5.6.7.8"


def test_x_forwarded_proto(simple_app):
    event = make_event(headers={"X-Forwarded-Proto": ["https"]})

    simple_app.handler(event, None)

    assert simple_app.environ["wsgi.url_scheme"] == "https"
    assert simple_app.environ["HTTP_X_FORWARDED_PROTO"] == "https"


def test_x_forwarded_port(simple_app):
    event = make_event(headers={"X-Forwarded-Port": ["123"]})

    simple_app.handler(event, None)

    assert simple_app.environ["SERVER_PORT"] == "123"
    assert simple_app.environ["HTTP_X_FORWARDED_PORT"] == "123"


def test_no_headers(simple_app):
    # allow headers to be missing from event
    event = make_event()
    del event["multiValueHeaders"]

    simple_app.handler(event, None)


def test_headers_None(simple_app):
    # allow headers to be 'None' from APIG test console
    event = make_event()
    event["multiValueHeaders"] = None

    simple_app.handler(event, None)


def test_exc_info(simple_app):
    try:
        raise ValueError("Example exception")
    except ValueError:
        simple_app.exc_info = sys.exc_info()

    with pytest.raises(ValueError) as excinfo:
        simple_app.handler(make_event(), None)

    assert str(excinfo.value) == "Example exception"


def test_request_context(simple_app):
    context = {"authorizer": {"user": "test@example.com"}}
    event = make_event(request_context=context)

    simple_app.handler(event, None)

    assert simple_app.environ["apig_wsgi.request_context"] == context


def test_full_event(simple_app):
    event = make_event()

    simple_app.handler(event, None)

    assert simple_app.environ["apig_wsgi.full_event"] == event


def test_elb_health_check(simple_app):
    """
    Check compatibility with health check events as per:
    https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html#enable-health-checks-lambda  # noqa: B950
    """
    event = {
        "requestContext": {"elb": {"targetGroupArn": "..."}},
        "httpMethod": "GET",
        "path": "/",
        "queryStringParameters": {},
        "headers": {"user-agent": "ELB-HealthChecker/2.0"},
        "body": "",
        "isBase64Encoded": False,
    }

    simple_app.handler(event, None)

    environ = simple_app.environ
    assert environ["SERVER_NAME"] == ""
    assert environ["SERVER_PORT"] == ""
    assert environ["wsgi.url_scheme"] == "http"


def test_context(simple_app):
    context = ContextStub(aws_request_id="test-request-id")

    simple_app.handler(make_event(), context)

    assert simple_app.environ["apig_wsgi.context"] == context
