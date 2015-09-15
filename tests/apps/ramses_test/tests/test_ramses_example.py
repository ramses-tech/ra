from os import path
import pytest
import webtest
from paste.deploy import loadapp
import ra


appdir = path.abspath(path.join(path.dirname(__file__), '..'))
ramlfile = path.join(appdir, 'api.raml')
testapp = webtest.TestApp('config:test.ini', relative_to=appdir)
api = ra.api(ramlfile, testapp)


def user_factory():
    import string
    import random
    name = ''.join(random.choice(string.ascii_lowercase) for _ in range(10))
    email = "{}@example.com".format(name)
    return dict(username=name, email=email, password=name)


@api.resource('/users')
def users_resource(users):

    @pytest.fixture
    def two_hundred():
        return 200

    @users.get
    def get(req, two_hundred):
        response = req()
        assert response.status_code == two_hundred

    @users.post
    def post_using_example(req):
        req(status=(201, 409))

    @users.post(factory=user_factory)
    def post_using_factory(req):
        response = req()
        username = req.data['username']
        assert username in response

    @users.resource('/{username}')
    def user_resource(user):

        @user.get
        def get(req):
            response = req()
            assert response.status_code == 200
