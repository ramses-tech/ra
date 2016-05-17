Autotest
========

``api.autotest()`` will generate a basic test for each method defined
in the RAML file.

The test is a basic test:

.. code-block:: python

    def test(req):
        req()

This uses the default factories (using the example values in the RAML for
request bodies) and default URI parameters (example values in ``uriParameters``
definitions in the RAML).

By setting up fixtures to pre-generate any objects needing to be referenced
by the examples, and defining your RAML examples carefully, you can test a
whole API using autotest. The basic tests check for an acceptable status
code and validate the response body and headers against the RAML definition
(if any).

``api.autotest()`` accepts the following (optional) settings:
- ``postrequest_sleep`` (default: 0.5): seconds to wait in between each method

If you want to pass headers, use alternate content types, custom factories,
etc., write those tests by hand (see `Writing Tests <./writing_tests.html>`_).

