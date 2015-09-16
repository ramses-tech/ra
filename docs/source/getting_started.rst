Getting Started
===============

Install Ra with pip in your existing WSGI API project:

.. code-block:: shell

    $ pip install ra

Though not required, Ra works best with apps wrapped by `WebTest
<http://webtest.pythonpaste.org/>`_:

.. code-block:: shell

    $ pip install webtest


Requirements
------------

* Python 2.7, 3.3 or 3.4
* WSGI-based app providing an API (this guide assume a `Ramses
  <http://ramses.readthedocs.org/>`_ app)
* API definition in `RAML <http://raml.org/>`_


Basic Example
-------------

This is a quick example using Ra and WebTest to test some API resources.

Assuming a simple RAML definition (and an app that implements it):

.. code-block:: yaml

    #%RAML 0.8
    # ./api.raml
    ---
    title: people API
    mediaType: application/json
    protocols: [HTTP]

    /people:
        post:
            description: Create a new person
            body:
                application/json:
                    example: { "name": "joe" }

Create a new test file:

.. code-block:: python

    # ./tests/test_api.py
    import ra
    import os
    import webtest


    appdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    ramlfile = os.path.join(appdir, 'api.raml')
    testapp = webtest.TestApp('config:test.ini', relative_to=appdir)

    api = ra.api(ramlfile, testapp)

    @api.resource('/people')
    def users_resource(users):

        @users.post
        def post(req):
            # the request will automatically use the example body from
            # the RAML definition
            response = req(status=201) # asserts status code is 201
            assert 'joe' in response

This loads the app described by the Paste Deploy file ``./test.ini``
and reads the RAML definition at ``./api.raml``.  Run tests with
``py.test tests/test_api.py``. Ra will read the RAML definition, make
a request ``POST /people`` with the example body ``{ "name": "joe" }``.

Most likely, this will succeed the first time, and fail on subsequent
runs as "joe" already exists. See `Writing Tests <./writing_tests.html>`_
for an example of using factories to generate unique request bodies, and
`Hooks <./hooks.html>`_ for using before/after hooks to set up a clean
testing environment.
