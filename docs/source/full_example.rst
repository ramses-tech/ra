Full Example
=============

A full example follows.

The RAML:

.. code-block:: yaml

    #%RAML 0.8
    # ./example.raml
    ---
    title: example API
    mediaType: application/json
    protocols: [HTTP]

    /users:
        get:
            description: Get users
        post:
            description: Create a new user
            body:
                application/json:
                    schema: !include schemas/user.json
                    example: { "username": "marcy" }

        /{username}:
            get:
                description: Get user by username

    # ...

.. code-block:: python

    # in tests/test_api.py:
    import ra
    import pytest

    api = ra.api('example.raml', app='config:test.ini')

    @pytest.fixture(autouse=True)
    def clear_database(request, req, app, examples):
        # Remember:
        # - ``req`` is the pre-bound Ra request for the current test
        # - ``request`` is a built-in pytest fixture that holds info about
        #   the current test context
        # - ``app`` is the webtest-wrapped application
        # - ``examples`` is a fixture providing the examples factory manager
        #   for generating data based on RAML ``example`` properties.
        import example_app
        example_app.clear_db()
        example_app.start_transaction()

        # login for authentication
        app.post('/login', { 'login': 'system', 'password': '123456' })

        if req.match(exclude='POST /users'):
            # Before any test, except for the one that creates a user,
            # we should create the user first.
            #
            # Passing 'user' to ``examples.build()``
            # means to use the example defined for ``POST /users``
            marcy = examples.build('user') # returns a dict
            example_app.create_user_in_db(marcy)

        @request.addfinalizer
        def fin():
            example_app.rollback_transaction()
            app.reset() # clear cookies; logout


    # defining a resource scope:

    @api.resource('/users')
    def users_resource(users):

        # scope-local pytest fixtures
        #
        # a resource scope acts just like a regular module scope
        # with respect to pytest fixtures:

        @pytest.fixture
        def two_hundred():
            return 200

        # defining tests for methods in this resource:

        @users.get
        def get(req, two_hundred):
            # ``req`` is a callable request object that is pre-bound to the app
            # that was passed into ``ra.api`` as well as the URI derived from
            # the resource (test scope) and method (test) decorators.
            #
            # This example uses the other scope-local fixture defined above.
            response = req()
            assert response.status_code == two_hundred

        @users.post
        def post_using_example(req):
            # By default, when JSON data needs to be sent in the request body,
            # Ra will look for an ``example`` property in the RAML definition
            # of the resource method's body and use that.
            #
            # As in WebTest request methods, you can specify the expected
            # status code(s), which will be test the response status.
            req(status=(201, 409))

        # defining a custom user factory; underscored functions are not
        # considered tests (but better to import factories from another module)
        def _user_factory():
            import string
            import random
            name = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
            email = "{}@example.com".format(name)
            return dict(username=name, email=email, password=name)

        # using the factory:

        @users.post(factory=_user_factory)
        def post_using_factory(req):
            response = req()
            username = req.data['username']
            assert username in response

        # defining a sub-resource:

        @users.resource('/{username}')
        def user_resource(user):

            # this resource will be requested at /users/{username}
            #
            # By default, Ra will look at the ``example`` property for
            # URI parameters as defined in the RAML, and fill the URI
            # template with that.

            @user.get
            def get(req):
                # This is equivalent to the autotest for a resource
                # and method:
                req()

    api.autotest() # autotests will be generated
