import pytest
from ra.hooks import Hooks


class TestHooks:
    @pytest.fixture
    def hooks(self):
        return Hooks()

    def test_add_callback(self, hooks, mocker):
        callback = mocker.Mock()

        hooks.before()(callback)
        cond = dict(only=None, exclude=None)
        assert (callback, cond) in hooks._hooks['before']

        cond = dict(only=['GET'], exclude=None)
        hooks.before(**cond)(callback)
        assert (callback, cond) in hooks._hooks['before']

    def test_run_callbacks(self, hooks, mocker):
        callback = mocker.Mock()

        hooks.before()(callback)
        hooks.run('before')
        callback.assert_called_with()

    @pytest.mark.parametrize("conditions,request_,expected", [
        (dict(only=['GET']), 'GET /foo', True),
        (dict(only=['GET']), 'POST /foo', False),
        (dict(only=['/foo']), 'POST /foo', True),
        (dict(only=['/foo']), 'POST /bar', False),
        (dict(only=['GET /foo']), 'GET /foo', True),
        (dict(only=['GET /foo']), 'POST /foo', False),
        (dict(only=['GET /foo']), 'GET /bar', False),

        (dict(exclude=['GET']), 'GET /foo', False),
        (dict(exclude=['GET']), 'POST /foo', True),
        (dict(exclude=['/foo']), 'POST /foo', False),
        (dict(exclude=['/foo']), 'POST /bar', True),
        (dict(exclude=['GET /foo']), 'GET /foo', False),
        (dict(exclude=['GET /foo']), 'POST /foo', True),
        (dict(exclude=['GET /foo']), 'GET /bar', True),

        (dict(only=['/foo'], exclude=['GET']), 'GET /foo', False),
        (dict(only=['/foo'], exclude=['GET']), 'POST /foo', True),

        (dict(only=['GET'], exclude=['/foo']), 'GET /foo', False),
        (dict(only=['GET'], exclude=['/foo']), 'GET /bar', True),
    ])
    def test_run_callbacks_with_conditions(self, hooks, mocker,
                                           conditions, request_, expected):
        callback = mocker.Mock()
        method, path = request_.split(' ')
        node = mocker.Mock(method=method, path=path)
        hooks.hookname(**conditions)(callback)
        hooks.run('hookname', node)
        if expected:
            callback.assert_called_with()
        else:
            callback.assert_not_called()
