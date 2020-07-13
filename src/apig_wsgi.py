import sys
from base64 import b64decode, b64encode
from io import BytesIO

__all__ = ("make_lambda_handler",)

DEFAULT_NON_BINARY_CONTENT_TYPE_PREFIXES = (
    "text/",
    "application/json",
    "application/vnd.api+json",
)


def make_lambda_handler(
    wsgi_app, binary_support=False, non_binary_content_type_prefixes=None
):
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
        `binray_support` is True. This prevents apig_wsgi from unexpectedly encoding
        non-binary responses as binary.
    """
    if non_binary_content_type_prefixes is None:
        non_binary_content_type_prefixes = DEFAULT_NON_BINARY_CONTENT_TYPE_PREFIXES
    non_binary_content_type_prefixes = tuple(non_binary_content_type_prefixes)

    def handler(event, context):
        environ = get_environ(event, context, binary_support=binary_support)
        response = Response(
            binary_support=binary_support,
            non_binary_content_type_prefixes=non_binary_content_type_prefixes,
        )
        result = wsgi_app(environ, response.start_response)
        response.consume(result)
        return response.as_apig_response()

    return handler


def get_environ(event, context, binary_support):
    method = event["httpMethod"]
    body = event.get("body", "") or ""
    if event.get("isBase64Encoded", False):
        body = b64decode(body)
    else:
        body = body.encode("utf-8")

    environ = {
        "CONTENT_LENGTH": str(len(body)),
        "HTTP": "on",
        "PATH_INFO": event["path"],
        "REMOTE_ADDR": "127.0.0.1",
        "REQUEST_METHOD": method,
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
    }

    # Multi-value query strings need explicit activation on ALB
    if "multiValueQueryStringParameters" in event:
        # may be None when testing on console
        multi_params = event["multiValueQueryStringParameters"] or {}
    else:
        single_params = event.get("queryStringParameters") or {}
        multi_params = {key: [value] for key, value in single_params.items()}
    environ["QUERY_STRING"] = "&".join(
        "{}={}".format(key, val) for (key, vals) in multi_params.items() for val in vals
    )

    # Multi-value headers need explicit activation on ALB
    if "multiValueHeaders" in event:
        # may be None when testing on console
        headers = event["multiValueHeaders"] or {}
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

    # Pass the AWS requestContext to the application
    if "requestContext" in event:
        environ["apig_wsgi.request_context"] = event["requestContext"]

    # Pass the full event to the application as an escape hatch
    environ["apig_wsgi.full_event"] = event
    environ["apig_wsgi.context"] = context

    return environ


class Response(object):
    def __init__(self, binary_support, non_binary_content_type_prefixes):
        self.status_code = 500
        self.headers = []
        self.body = BytesIO()
        self.binary_support = binary_support
        self.non_binary_content_type_prefixes = non_binary_content_type_prefixes

    def start_response(self, status, response_headers, exc_info=None):
        if exc_info is not None:
            raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
        self.status_code = int(status.split()[0])
        self.headers.extend(response_headers)
        return self.body.write

    def consume(self, result):
        try:
            for data in result:
                if data:
                    self.body.write(data)
        finally:
            if hasattr(result, "close"):
                result.close()

    def as_apig_response(self):
        response = {"statusCode": self.status_code, "headers": dict(self.headers)}
        if self._should_send_binary():
            response["isBase64Encoded"] = True
            response["body"] = b64encode(self.body.getvalue()).decode("utf-8")
        else:
            response["body"] = self.body.getvalue().decode("utf-8")

        return response

    def _should_send_binary(self):
        """
        Determines if binary response should be sent to API Gateway
        """
        if not self.binary_support:
            return False

        content_type = self._get_content_type()
        if not content_type.startswith(self.non_binary_content_type_prefixes):
            return True

        content_encoding = self._get_content_encoding()
        # Content type is non-binary but the content encoding might be.
        return "gzip" in content_encoding.lower()

    def _get_content_type(self):
        return self._get_header("content-type") or ""

    def _get_content_encoding(self):
        return self._get_header("content-encoding") or ""

    def _get_header(self, header_name):
        header_name = header_name.lower()
        matching_headers = [v for k, v in self.headers if k.lower() == header_name]
        if len(matching_headers):
            return matching_headers[-1]
        return None
