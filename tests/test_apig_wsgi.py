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
    headers=None,
    body="",
    binary=False,
    request_context=None,
):
    if headers is None:
        headers = {"Host": "example.com"}

    event = {
        "httpMethod": method,
        "path": "/",
        "queryStringParameters": qs_params,
        "headers": headers,
    }

    if binary:
        event["body"] = b64encode(body.encode("utf-8"))
        event["isBase64Encoded"] = True
    else:
        event["body"] = body

    if request_context is not None:
        event["requestContext"] = request_context

    return event


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


def test_querystring_empty(simple_app):
    event = make_event(qs_params={})

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == ""


def test_querystring_one(simple_app):
    event = make_event(qs_params={"foo": "bar"})

    simple_app.handler(event, None)

    assert simple_app.environ["QUERY_STRING"] == "foo=bar"


def test_plain_header(simple_app):
    event = make_event(headers={"Test-Header": "foobar"})

    simple_app.handler(event, None)

    assert simple_app.environ["HTTP_TEST_HEADER"] == "foobar"


def test_special_headers(simple_app):
    event = make_event(
        headers={
            "Content-Type": "text/plain",
            "Host": "example.com",
            "X-Forwarded-For": "1.2.3.4, 5.6.7.8",
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Port": "123",
        }
    )

    simple_app.handler(event, None)

    assert simple_app.environ["CONTENT_TYPE"] == "text/plain"
    assert simple_app.environ["SERVER_NAME"] == "example.com"
    assert simple_app.environ["REMOTE_ADDR"] == "1.2.3.4"
    assert simple_app.environ["wsgi.url_scheme"] == "https"
    assert simple_app.environ["SERVER_PORT"] == "123"


def test_no_headers(simple_app):
    # allow headers to be missing from event
    event = make_event()
    del event["headers"]

    simple_app.handler(event, None)


def test_headers_None(simple_app):
    # allow headers to be 'None' from APIG test console
    event = make_event()
    event["headers"] = None

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
