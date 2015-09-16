"""
Ra is a test helper and pytest plugin for testing APIs defined by RAML
files.

It can be used with pytest and webtest to write functional tests for
APIs a natural way that mirrors the structure of the RAML file.

Ra also provides default automatic testing of resources defined in the
RAML to validate responses.

"""
from .api import APIError
from . import raml


def api(raml, app, JSONEncoder=None):
    """The main entry point for Ra.

    :param raml:        either a path to a RAML file, or a RAML string
    :param app:         a ``webtest.TestApp``-like app to make requests against
    :param JSONEncoder: an optional JSONEncoder class to encode data used in
                        request bodies.

    :return: instance of ``ra.API``, used to define the test suite
    """
    from .api import API
    return API(raml, app, JSONEncoder=JSONEncoder)
