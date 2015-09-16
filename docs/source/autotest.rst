Autotest
========

``api.autotest()`` will generate a test for each method defined in the RAML.

The test is a basic test:

.. code-block:: python

    def test(req):
      req()

This uses the default factories (using the example values in the RAML for
request bodies) and default URI parameters (example values in ``uriParameters``
definitions in the RAML).

By setting up hooks to pre-generate any objects needing to be referenced
by the examples, and defining your RAML examples carefully, you can test a
whole API using autotest. The basic tests check for an acceptable status
code and validate the response body and headers against the RAML definition
(if any).

If you want to pass headers, use alternate content types, custom factories,
etc., write those tests by hand (see `Writing Tests <./writing_tests.html>`_).

