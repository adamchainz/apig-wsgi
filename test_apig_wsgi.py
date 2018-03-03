# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from io import BytesIO

from apig_wsgi import make_lambda_handler


def hello_world_app(environ, start_response):
    body = environ['wsgi.input'].read()
    start_response('200 OK', [('Content-type', 'text/plain')])

    if environ['REQUEST_METHOD'] == 'POST':
        return BytesIO(body)
    return BytesIO(b'Hello World\n')


hello_world_handler = make_lambda_handler(hello_world_app)


def make_event(method='GET', qs_params=None, headers=None, body=''):
    if qs_params is None:
        qs_params = {}
    if headers is None:
        headers = {
            'Host': 'example.com',
        }

    return {
        'httpMethod': method,
        'path': '/',
        'queryStringParameters': qs_params,
        'headers': headers,
        'body': body,
    }


def test_get():
    response = hello_world_handler(make_event(), None)

    assert response == {
        'statusCode': '200',
        'headers': {'Content-type': 'text/plain'},
        'body': b'Hello World\n',
    }


def test_post():
    event = make_event(method='POST', body='The World Is Large')

    response = hello_world_handler(event, None)

    assert response == {
        'statusCode': '200',
        'headers': {'Content-type': 'text/plain'},
        'body': b'The World Is Large',
    }


def test_plain_header():
    def app(environ, start_response):
        start_response('200 OK', [])
        val = environ.get('HTTP_TEST_HEADER', '')
        return BytesIO(val.encode('utf-8'))
    handler = make_lambda_handler(app)
    event = make_event(headers={'Test-Header': 'foobar'})

    response = handler(event, None)

    assert response['body'] == b'foobar'


def test_special_headers():
    event = make_event(headers={
        'Content-Type': 'text/plain',
        'Host': 'example.com',
        'X-Forwarded-For': '1.2.3.4, 5.6.7.8',
        'X-Forwarded-Proto': 'https',
        'X-Forwarded-Port': '123',
    })

    def app(environ, start_response):
        start_response('200 OK', [])
        app.environ = environ
        return BytesIO()
    handler = make_lambda_handler(app)

    handler(event, None)

    assert app.environ['CONTENT_TYPE'] == 'text/plain'
    assert app.environ['SERVER_NAME'] == 'example.com'
    assert app.environ['REMOTE_ADDR'] == '1.2.3.4'
    assert app.environ['wsgi.url_scheme'] == 'https'
    assert app.environ['SERVER_PORT'] == '123'
