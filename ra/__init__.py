"""
Ra is a test helper and pytest plugin for testing APIs defined by RAML
files.

It can be used with pytest and webtest to write functional tests for
APIs a natural way that mirrors the structure of the RAML file.

Ra also provides default automatic testing of resources defined in the
RAML to validate responses.

"""
from . import raml
from .dsl import APISuite


def api(raml, app, JSONEncoder=None):
    """The main entry point for Ra.

    :param raml:        either a path to a RAML file, or a RAML string
    :param app:         a ``webtest.TestApp``-like app to make requests against
    :param JSONEncoder: an optional JSONEncoder class to encode data used in
                        request bodies.

    :return: instance of ``ra.APISuite``, used to define the test suite
    """
    return APISuite(raml, app, JSONEncoder=JSONEncoder)
