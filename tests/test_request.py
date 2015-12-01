import pytest
from ra.request import _match_request


class TestRequest:
    @pytest.mark.parametrize("conditions,method,path,expected", [
        (dict(only=['GET']), 'GET', '/foo', True),
        (dict(only='GET'), 'GET', '/foo', True),
        (dict(only=['GET']), 'POST', '/foo', False),
        (dict(only=['/foo']), 'POST', '/foo', True),
        (dict(only=['/foo']), 'POST', '/bar', False),
        (dict(only=['GET /foo']), 'GET', '/foo', True),
        (dict(only=['GET /foo']), 'POST', '/foo', False),
        (dict(only=['GET /foo']), 'GET', '/bar', False),

        (dict(exclude=['GET']), 'GET', '/foo', False),
        (dict(exclude=['GET']), 'POST', '/foo', True),
        (dict(exclude=['/foo']), 'POST', '/foo', False),
        (dict(exclude=['/foo']), 'POST', '/bar', True),
        (dict(exclude=['GET /foo']), 'GET', '/foo', False),
        (dict(exclude=['GET /foo']), 'POST', '/foo', True),
        (dict(exclude=['GET /foo']), 'GET', '/bar', True),

        (dict(only=['/foo'], exclude=['GET']), 'GET', '/foo', False),
        (dict(only=['/foo'], exclude=['GET']), 'POST', '/foo', True),

        (dict(only=['GET'], exclude=['/foo']), 'GET', '/foo', False),
        (dict(only=['GET'], exclude=['/foo']), 'GET', '/bar', True),
    ])
    def test_match_request(self, conditions, method, path, expected):
        assert bool(_match_request(path, method, **conditions)) == expected
