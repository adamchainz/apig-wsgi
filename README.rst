=========
apig-wsgi
=========

.. image:: https://img.shields.io/travis/adamchainz/apig-wsgi/master.svg
        :target: https://travis-ci.org/adamchainz/apig-wsgi

.. image:: https://img.shields.io/pypi/v/apig-wsgi.svg
        :target: https://pypi.python.org/pypi/apig-wsgi

Wrap a WSGI application in an AWS Lambda handler function for running on
API Gateway.

A quick example:

.. code-block:: python

    from apig_wsgi import make_lambda_handler
    from myapp.wsgi import app

    # Configure this as your entry point in AWS Lambda
    lambda_handler = make_lambda_handler(app)


Installation
============

Use **pip**:

.. code-block:: sh

    pip install apig-wsgi

Tested on Python versions 2.7 and 3.7.

Usage
=====

``make_lambda_handler(app, binary_support=False)``
--------------------------------------------------

``app`` should be a WSGI app, for example from Django's ``wsgi.py`` or Flask's
``Flask()`` object.

If you want to support sending binary responses, set ``binary_support`` to
``True`` and make sure you have ``'*/*'`` in the 'binary media types'
configuration on your Rest API on API Gateway. Note, whilst API Gateway
supports a list of binary media types, using ``'*/*'`` is the best way to do
it, since it is used to match the request 'Accept' header as well, which most
applications ignore.

Note that binary responses aren't sent if your response has a 'Content-Type'
starting 'text/html' or 'application/json' - this is to support sending larger
text responses.
