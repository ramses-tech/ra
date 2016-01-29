"""
Ra is a test helper and pytest plugin for testing APIs defined by RAML
files.

It can be used with pytest and webtest to write functional tests for
APIs a natural way that mirrors the structure of the RAML file.

Ra also provides default automatic testing of resources defined in the
RAML to validate responses.

"""
from .dsl import APISuite


def api(raml, app='config:test.ini', relative_to=None, JSONEncoder=None):
    """The main entry point for Ra.

        :param raml:        path to RAML file or RAML in string form
        :param app:         can be either a callable WSGI application, a
                            ``webtest.TestApp`` instance, a string describing
                            a Paste Deploy app (like 'config:test.ini') or a
                            full URL to a proxy server (requires
                            ``WSGIProxy2``).
        :param relative_to: used to locate the raml file or Paste Deploy
                            config if relative paths are used. The default is
                            an educated guess.
        :param JSONEncoder: an optional JSONEncoder class to encode data used
                            in request bodies.

    :return: instance of ``ra.APISuite``, used to define the test suite
    """
    return APISuite(raml, app, relative_to, JSONEncoder)
