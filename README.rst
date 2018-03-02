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

Tested on Python 2.7 and Python 3.6.
