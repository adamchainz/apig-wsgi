# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from io import BytesIO

import six
from six.moves.urllib_parse import urlencode

__author__ = 'Adam Johnson'
__email__ = 'me@adamj.eu'
__version__ = '1.0.0'

__all__ = ('make_lambda_handler',)


def make_lambda_handler(wsgi_app):
    """
    Turn a WSGI app callable into a Lambda handler function suitable for
    running on API Gateway.
    """
    def handler(event, context):
        environ = get_environ(event)
        response = Response()
        result = wsgi_app(environ, response.start_response)
        response.consume(result)
        return response.as_apig_response()
    return handler


def get_environ(event):
    params = event.get('queryStringParameters') or {}
    body = (event.get('body', '') or '').encode('utf-8')

    environ = {
        'CONTENT_LENGTH': str(len(body)),
        'HTTP': 'on',
        'PATH_INFO': event['path'],
        'QUERY_STRING': urlencode(params),
        'REMOTE_ADDR': '127.0.0.1',
        'REQUEST_METHOD': event['httpMethod'],
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
    for key, value in six.iteritems(headers):
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
    def __init__(self):
        self.status_code = '500'
        self.headers = []
        self.body = BytesIO()

    def start_response(self, status, response_headers, exc_info=None):
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
        return {
            'statusCode': self.status_code,
            'headers': dict(self.headers),
            'body': self.body.getvalue().decode('utf-8')
        }
