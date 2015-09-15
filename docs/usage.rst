Example usage::

    # in tests/test_api.py:
    import os
    import ra
    import webtest

    appdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    ramlfile = os.path.join(appdir, 'api.raml')
    testapp = webtest.TestApp('config:test.ini', relative_to=appdir)
    api = ra.api(ramlfile, testapp)

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
                # This is equivalent to the default test for a resource
                # and method:
                req()

