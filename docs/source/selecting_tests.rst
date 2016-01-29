Selecting Tests
===============

On the commandline, you can select a subset of tests to run by referring
to their pytest node IDs.

For the following example resource:

.. code-block:: python

    # in ./tests/test_api.py

    @api.resource('/users')
    def users_resource(users):

        @users.get
        def get(req): req()

        @users.post
        def post(req): req()

You can select only the tests in this resource like this:

.. code-block:: shell

    $ py.test tests/test_api.py::/users

To select a single test, append the function name:
``tests/test_api.py::/users::get``

For autotests, insert "autotests" before the resource name:
``tests/test_api.py::autotests::/users::get``

See `the pytest docs
<https://pytest.org/latest/example/markers.html#selecting-tests-based-on-their-node-id>`_
for details.
