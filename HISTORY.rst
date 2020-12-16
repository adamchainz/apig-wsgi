=======
History
=======

2.10.0 (2020-12-16)
-

* Drop Python 3.5 support.

2.9.2 (2020-10-16)
------------------

* Unquote paths, as per the WSGI specification. This fixes a bug where paths
  like ``/api/path%2Finfo"`` were not correctly received by the application as
  ``/api/path/info"``
  (`Pull Request #188 <https://github.com/adamchainz/apig-wsgi/pull/188>`__).

2.9.1 (2020-10-13)
------------------

* Support Python 3.9.
* Fix query string parameter encoding so that symbols are correctly re-encoded
  for WSGI, for API Gateway format version 1
  (`Issue #186 <https://github.com/adamchainz/apig-wsgi/pull/186>`__).

2.9.0 (2020-10-12)
------------------

* Move license from ISC to MIT License.
* Always send ``isBase64Encoded`` in responses, as per the AWS documentation.
* Support `format version
  2 <https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html>`,
  which was introduced by API Gateway for “HTTP API's”
  (`Issue #124 <https://github.com/adamchainz/apig-wsgi/pull/124>`__)..
* ``binary_support`` now defaults to ``None``, which means that it will
  automatically enable binary support for format version 2 events.

2.8.0 (2020-07-20)
------------------

* Use multi-value headers in the response when given in the request.
  (`PR #157 <https://github.com/adamchainz/apig-wsgi/pull/157>`__).

2.7.0 (2020-07-13)
------------------

* Add defaults for ``SERVER_HOST``, ``SERVER_PORT`` and ``wsgi.url_scheme``.
  This enables responding to `ELB health check events
  <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html#enable-health-checks-lambda>`__,
  which don't contain the relevant headers
  (`Issue #155 <https://github.com/adamchainz/apig-wsgi/pull/155>`__).

2.6.0 (2020-03-07)
------------------

* Pass Lambda Context object as a WSGI environ variable
  (`PR #122 <https://github.com/adamchainz/apig-wsgi/pull/122>`__).

2.5.1 (2020-02-26)
------------------

* Restore setting ``HTTP_CONTENT_TYPE`` and ``HTTP_HOST`` in the environ,
  accidentally broken in 2.5.0 with multi-value header feature
  (`Issue #117 <https://github.com/adamchainz/apig-wsgi/issues/117>`__).

2.5.0 (2020-02-17)
------------------

* Support multi-value headers and query parameters as API Gateway added
  (`Issue #103 <https://github.com/adamchainz/apig-wsgi/issues/103>`__).
* Pass full event as a WSGI environ variable
  (`PR #111 <https://github.com/adamchainz/apig-wsgi/issues/111>`__).

2.4.1 (2020-01-13)
------------------

* Fix URL parameter encoding - URL escaping like `%3A` will now be passed
  correctly to your application
  (`Issue #101 <https://github.com/adamchainz/apig-wsgi/issues/101>`__).
  Whilst this is a bugfix release, it may break any workarounds you have in
  your application - please check when upgrading.

2.4.0 (2019-11-15)
------------------

* Converted setuptools metadata to configuration file. This meant removing the
  ``__version__`` attribute from the package. If you want to inspect the
  installed version, use
  ``importlib.metadata.version("apig-wsgi")``
  (`docs <https://docs.python.org/3.8/library/importlib.metadata.html#distribution-versions>`__ /
  `backport <https://pypi.org/project/importlib-metadata/>`__).
* Support Python 3.8.
* Add `application/vnd.api+json` to default non-binary content type prefixes.
* Add support for custom non-binary content type prefixes. This lets you control
  which content types should be treated as plain text when binary support is enabled.

2.3.0 (2019-08-19)
------------------

* Update Python support to 3.5-3.7, as 3.4 has reached its end of life.
* Return binary content for gzipped responses with text or JSON content types.

2.2.0 (2019-04-15)
------------------

* If API Gateway event includes ``requestContext``, for example for custom
  authorizers, pass it in the WSGI ``environ`` as
  ``apig_wsgi.request_context``.

2.1.1 (2019-03-31)
------------------

* Revert adding ``statusDescription`` because it turns out API Gateway doesn't
  ignore it but instead fails the response with an internal server error.

2.1.0 (2019-03-31)
------------------

* Change ``statusCode`` returned to API Gateway / ALB to an integer. It seems
  API Gateway always supported both strings and integers, whilst ALB only
  supports integers.
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
  is needed with a higher version number for ``python -m pip install apig-wsgi`` to
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
