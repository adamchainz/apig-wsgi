History
-------

Pending Release
---------------

.. Insert new release notes below this line

2.1.0 (2019-03-31)
------------------

* Change ``statusCode`` returned to API Gateway / ALB to an integer. It seems
  API Gateway always supported both strings and integers, whilst API Gateway
  only supports integers.
* Add ``statusDescription`` in return value. API Gateway doesn't seem to use
  this whilst the `ALB documentation <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html>`_
  mentions it as supported.

2.0.2 (2019-02-07)
------------------

* Drop Python 2 support, only Python 3.4+ is supported now.

2.0.1 (2019-02-07)
------------------

* Temporarily restore Python 2 support. This is in order to fix a packaging
  metadata issue that 2.0.0 was marked as supporting Python 2, so a new release
  is needed with a higher version number for ``pip install apig-wsgi`` to
  resolve properly on Python 2. Version 2.0.2+ of ``apig-wsgi`` will not
  support Python 2.

2.0.0 (2019-01-28)
------------------

* Drop Python 2 support, only Python 3.4+ is supported now.
* If ``exc_info`` is passed in, re-raise the exception (previously it would be
  ignored and crash in a different way). This isn't the nicest experience,
  however the behaviour is copied from ``wsgiref``\'s simple server, and most
  WSGI applications implement their own exception conversion to a "500 Internal
  Server Error" page already.
* Noted that the EC2 ALB to Lambda integration is also supported as it uses the
  same event format as API Gateway.

1.2.0 (2018-05-14)
------------------

* Work with base64 encoded ``body`` values in requests from API Gateway.

1.1.2 (2018-05-11)
------------------

* Fix crash using binary support for responses missing a ``Content-Type``
  header.

1.1.1 (2018-05-11)
------------------

* Remove debug ``print()``

1.1.0 (2018-05-10)
------------------

* Add ``binary_support`` flag to enable sending binary responses, if enabled on
  API Gateway.

1.0.0 (2018-03-08)
------------------

* First release on PyPI, working basic integration for WSGI apps on API
  Gateway.
