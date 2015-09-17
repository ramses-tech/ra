Factories
=========

Ra will automatically use example values from the RAML definition for
request bodies when they're defined. However, this can be overridden by
passing factory arguments to scopes or tests.


Example factories
-----------------

When Ra reads the RAML definition, it will grab the example request body
values of type "application/json" for each resource and create a factory
function that returns that example, optionally overriding keys in the
example.

Example factories are accessible through the ``ra.API`` object. For the
following example RAML:

.. code-block:: yaml

    /users:
        post:
            body:
                application/json:
                    example: { "username": "simon" }
        /{username}:
            put:
                body:
                    application/json:
                        example: { "username": "gunther" }
            /profile:
                post:
                    body:
                        application/json:
                            example: { "address": "ice kingdom" }

Ra will create example these example factories:

.. code-block:: python

    api = ra.api(ramlfile, testapp)

    post_users_factory = api.examples.get_factory("POST /users")
    post_users_factory() == { "username": "simon" }

    # the POST body example is also keyed under the singular resource name:
    user_factory = api.examples.get_factory("user")
    post_users_factory is user_factory

    # you can build examples directly:
    put_user_example = api.examples.build("PUT /users/{username}")

    # and you can override keys in the example:
    profile_factory = api.examples.get_factory("POST /users/{username}/profile")
    profile1 = profile_factory(address="ooo")

    # singular resource names drop dynamic segments:
    profile2 = api.examples.build("user.profile", address="ooo")
    profile1 == profile2 == { "address": "ooo" }

Example factories are the default factories used to create request bodies
whenever they're defined. If a body is defined for a method but no example
is defined, the example factory for the resource's POST method will be
used as a fallback. Thus, you can get away with defining examples only on
POST bodies for each collection resource (the same example that is keyed to
the dotted resource name).


Overriding Factories
--------------------

You can pass a custom factory into resource scope or test declaration
decorators to override the example factory (or provide a factory when
no example is defined). You can also access the factory on the ``req``
request object to override attributes.

.. code-block:: python

    @api.resource("/users", factory=my_user_factory)
    def users_resource(users):

        # tests in this scope will use my_user_factory instead
        # of an example factory

        @users.post(factory=my_other_factory)
        def post(req):
            # this test will use my_other_factory instead

            # if you want to override attributes:
            req.data = req.factory(username="james")

        # ...
