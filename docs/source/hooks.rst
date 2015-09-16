Hooks
=====

Before/after hooks provide a way to do setup/teardown around tests, scopes
and the whole suite.

Hooks are implemented using pytest "autouse" fixtures. In many cases,
you could use pytest fixtures directly to do setup/teardown,
though before/after hooks are probably more expressive.

Where hooks become more useful is when you want to filter the
tests that they apply to by resource path or request method:

.. code-block:: python

    @api.hooks.before_each
    def clear_database():
        from myapp import clear_database
        clear_database()

    @api.hooks.before_each(only=['/users'], exclude=['POST'])
    def create_user():
        from myapp import create_user
        create_user("marcy")

    def user_factory():
        user = {
            'username': 'marcy',
            #  ...
        }
        return user

    @api.resource('/users')
    def users_resource(users):
        @users.get
        def get(req):
            response = req()
            assert 'marcy' in response

        @users.post(factory=user_factory)
        def post(req):
            response = req()
            assert 'marcy' in response

In this example, we use a ``before_each`` hook to clear the database
in between each test. (You could also begin and rollback database
transactions in before/after_each hooks.)

The second hook definition runs the decorated function only for
tests on the ``/users`` resource, for all HTTP methods except ``POST``.
This means the user exists for the GET request, but not for the POST
request where it will be created by the request (to avoid conflict).

This ensures that tests are isolated from one another, but still
have access to the objects they expect (based on the examples in the
RAML, for example).

API hooks
---------

These hooks are run once, before or after the entire test suite:

    - ``api.hooks.before_all``
    - ``api.hooks.after_all``

These hooks are run before or after each test in the test suite:

    - ``api.hooks.before_each``
    - ``api.hooks.after_each``

Resource Hooks
--------------

Resource hooks are local to the resource scope.

These hooks run once, before or after all tests in the resource scope:

    - ``resource_scope.hooks.before_all``
    - ``resource_scope.hooks.after_all``

These hooks run before or after each test in the resource scope:

    - ``resource_scope.hooks.before_each``
    - ``resource_scope.hooks.after_each``

Where ``resource_scope`` is the object passed into the resource scope
function (``users`` in the example above).
