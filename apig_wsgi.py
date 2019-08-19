import sys
from base64 import b64decode, b64encode
from io import BytesIO
from urllib.parse import urlencode

__author__ = "Adam Johnson"
__email__ = "me@adamj.eu"
__version__ = "2.3.0"

__all__ = ("make_lambda_handler",)


def make_lambda_handler(wsgi_app, binary_support=False):
    """
    Turn a WSGI app callable into a Lambda handler function suitable for
    running on API Gateway.
    """

    def handler(event, context):
        environ = get_environ(event, binary_support=binary_support)
        response = Response(binary_support=binary_support)
        result = wsgi_app(environ, response.start_response)
        response.consume(result)
        return response.as_apig_response()

    return handler


def get_environ(event, binary_support):
    method = event["httpMethod"]
    body = event.get("body", "") or ""
    if event.get("isBase64Encoded", False):
        body = b64decode(body)
    else:
        body = body.encode("utf-8")
    params = event.get("queryStringParameters") or {}

    environ = {
        "CONTENT_LENGTH": str(len(body)),
        "HTTP": "on",
        "PATH_INFO": event["path"],
        "QUERY_STRING": urlencode(params),
        "REMOTE_ADDR": "127.0.0.1",
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.errors": sys.stderr,
        "wsgi.input": BytesIO(body),
        "wsgi.multiprocess": False,
        "wsgi.multithread": False,
        "wsgi.run_once": False,
        "wsgi.version": (1, 0),
    }

    headers = event.get("headers") or {}  # may be None when testing on console
    for key, value in headers.items():
        key = key.upper().replace("-", "_")

        if key == "CONTENT_TYPE":
            environ["CONTENT_TYPE"] = value
        elif key == "HOST":
            environ["SERVER_NAME"] = value
        elif key == "X_FORWARDED_FOR":
            environ["REMOTE_ADDR"] = value.split(", ")[0]
        elif key == "X_FORWARDED_PROTO":
            environ["wsgi.url_scheme"] = value
        elif key == "X_FORWARDED_PORT":
            environ["SERVER_PORT"] = value

        environ["HTTP_" + key] = value

    # Pass the AWS requestContext to the application
    if "requestContext" in event:
        environ["apig_wsgi.request_context"] = event["requestContext"]

    return environ


class Response(object):
    def __init__(self, binary_support):
        self.status_code = 500
        self.headers = []
        self.body = BytesIO()
        self.binary_support = binary_support

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
        non_binary_content_types = ("text/", "application/json")
        if not content_type.startswith(non_binary_content_types):
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
