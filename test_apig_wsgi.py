# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from io import BytesIO

from apig_wsgi import make_lambda_handler


def hello_world_app(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    return BytesIO(b'Hello World\n')


def make_event():
    return {
        'httpMethod': 'GET',
        'path': '/',
        'queryStringParameters': {},
        'body': '',
        'headers': {
            'Content-Type': 'text/plain',
            'Host': 'example.com',
            'X-Forwarded-For': '1',
            'X-Forwarded-Proto': 'https',
            'X-Forwarded-Port': '123',
            'User-Agent': 'test-bot',
        }
    }


def test_basic():
    handler = make_lambda_handler(hello_world_app)

    response = handler(make_event(), None)

    assert response == {
        'statusCode': '200',
        'headers': {'Content-type': 'text/plain'},
        'body': b'Hello World\n',
    }
