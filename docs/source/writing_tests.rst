Writing Tests
=============

Ra uses a simple DSL for describing tests in a structured way, similar
to the RAML definition.

Resource scopes:
----------------

Tests are organized by resource in "resource scopes", which can be nested:

.. code-block:: python

    api = ra.api(ramlfile, testapp)
    @api.resource('/users')
    def users_resource(users):

        # tests for /users resource

        @users.resource('/{username}')
        def user_resource(user):

            # tests for /users/{username} resource

The resource scope (e.g. function ``users_resource`` above) takes an
argument: it will be passed a ``ResourceScope`` object that is used
within the scope to define tests or nested scopes.

By default, requests made in resource tests will use the example body
defined in the RAML if it exists (only 'application/json' is currently
supported). You can override this behaviour and use custom resource
factories:

.. code-block:: python

    def user_factory():
        import string
        import random
        name = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
        email = "{}@example.com".format(name)
        return dict(username=name, email=email, password=name)

    @api.resource('/users')
    def users_resource(users, factory=user_factory):

        # tests ...

Also by default, resources with URI parameters will have the parameter
filled with the example value defined in the RAML if it exists. It can
be overrided when the scope is declared:

.. code-block:: yaml

    # ...
    /users/{username}:
        uriParameters:
            username:
                type: string
                example: finn

.. code-block:: python

    # ...
    @users.resource('/users/{username}')
    def user_resource(user):
        # {username} will be "finn"
        # ...

    # or:

    @users.resource('/users/{username}', username='jake')
    def user_resource_overriding_username(user):
        # {username} will be "jake"
        # ...

Either way, for testing an item resource, you'll probably want to use
before hooks (see `Hooks <./hooks.html>`_) to set up a resource by that
name before these tests.

pytest fixtures defined in resource scopes are local to that scope
(behind the scenes, resource scopes are treated just like modules
by pytest):

.. code-block:: python

    @users.resource('/users')
    def users_resource(users):

        # local to this scope:
        @pytest.fixture
        def myfixture():
            return 1

        # ...


Tests
-----

Within resource scopes, define tests for the methods available on that
resource.

.. code-block:: python

    @users.resource('/users')
    def users_resource(users):

        @user.get
        def get(req):
            # do some test-specific setup ...
            response = req()
            # do some WebTest assertions on the response ...

The test function parameter ``req`` is provided by a pytest fixture.
It's a callable ``webob.request.RequestBase``-like request object that
is pre-bound to the app that was passed into ``ra.api(ramlfile, testapp)``,
as well as the resource scope's path and the test's method declaration.
(Note on ``req`` naming: ``request`` is already a builtin fixture name
in pytest.)

To override request parameters, you can pass them into the test
decorator:

.. code-block:: python

    @user.get(content_type='text/plain')
    def get_text(req):
        req()

Or pass them directly into ``req()``. You can also pass which status
codes are considered a success (default is 2xx/3xx status codes, this is
standard WebTest):

.. code-block:: python

    @users.get
    def get_text(req):
        req(content_type='text/plain', status=(200, 404))

You can also override the resource scope's factory declaration
(or the default RAML example factories) on individual tests:

.. code-block:: python

    @api.resource('/users', factory=users_factory)
    def users_resource(users):

        @users.post(factory=users_post_factory)
        def post_with_my_factory(req):
            assert req.factory == users_post_factory
            req()

By default, responses are validated against the RAML definition,
checking the body and headers are compliant. You can disable this:

.. code-block:: python

    @user.get
    def get_with_my_factory(req):
        req(validate=False)
        # or only validate body
        req(validate=['body'])

Because tests are collected by pytest, you can pass any other fixtures
you want to the test function:

.. code-block:: python

    @pytest.fixture
    def two_hundred():
        return 200

    @user.get
    def get_with_fixture(req, two_hundred):
        response = req()
        assert response.status_code == two_hundred
