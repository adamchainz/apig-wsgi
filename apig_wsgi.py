import sys
from base64 import b64decode, b64encode
from io import BytesIO
from urllib.parse import urlencode

__author__ = 'Adam Johnson'
__email__ = 'me@adamj.eu'
__version__ = '2.0.0'

__all__ = ('make_lambda_handler',)


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
    method = event['httpMethod']
    body = event.get('body', '') or ''
    if event.get('isBase64Encoded', False):
        body = b64decode(body)
    else:
        body = body.encode('utf-8')
    params = event.get('queryStringParameters') or {}

    environ = {
        'CONTENT_LENGTH': str(len(body)),
        'HTTP': 'on',
        'PATH_INFO': event['path'],
        'QUERY_STRING': urlencode(params),
        'REMOTE_ADDR': '127.0.0.1',
        'REQUEST_METHOD': method,
        'SCRIPT_NAME': '',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.errors': sys.stderr,
        'wsgi.input': BytesIO(body),
        'wsgi.multiprocess': False,
        'wsgi.multithread': False,
        'wsgi.run_once': False,
        'wsgi.version': (1, 0),
    }

    headers = event.get('headers') or {}  # may be None when testing on console
    for key, value in headers.items():
        key = key.upper().replace('-', '_')

        if key == 'CONTENT_TYPE':
            environ['CONTENT_TYPE'] = value
        elif key == 'HOST':
            environ['SERVER_NAME'] = value
        elif key == 'X_FORWARDED_FOR':
            environ['REMOTE_ADDR'] = value.split(', ')[0]
        elif key == 'X_FORWARDED_PROTO':
            environ['wsgi.url_scheme'] = value
        elif key == 'X_FORWARDED_PORT':
            environ['SERVER_PORT'] = value

        environ['HTTP_' + key] = value

    return environ


class Response(object):
    def __init__(self, binary_support):
        self.status_code = '500'
        self.headers = []
        self.body = BytesIO()
        self.binary_support = binary_support

    def start_response(self, status, response_headers, exc_info=None):
        if exc_info is not None:
            raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
        self.status_code = status.split()[0]
        self.headers.extend(response_headers)
        return self.body.write

    def consume(self, result):
        try:
            for data in result:
                if data:
                    self.body.write(data)
        finally:
            if hasattr(result, 'close'):
                result.close()

    def as_apig_response(self):
        response = {
            'statusCode': self.status_code,
            'headers': dict(self.headers),
        }

        content_type = self._get_content_type()
        should_send_binary = (
            self.binary_support and (
                content_type is None or
                not content_type.startswith(('text/', 'application/json'))
            )
        )

        if should_send_binary:
            response['isBase64Encoded'] = True
            response['body'] = b64encode(self.body.getvalue()).decode('utf-8')
        else:
            response['body'] = self.body.getvalue().decode('utf-8')

        return response

    def _get_content_type(self):
        content_type_headers = [v for k, v in self.headers if k.lower() == 'content-type']
        if len(content_type_headers):
            return content_type_headers[-1]
        return None
