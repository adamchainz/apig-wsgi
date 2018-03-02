# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__author__ = 'Adam Johnson'
__email__ = 'me@adamj.eu'
__version__ = '1.0.0'

__all__ = ('make_lambda_handler',)


def make_lambda_handler(wsgi_app):
    """
    Turn a WSGI app callable into a Lambda handler function suitable for
    running on API Gateway.
    """
    def wrapper(*args, **kwargs):
        return wsgi_app(*args, **kwargs)
    return wrapper
