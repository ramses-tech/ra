import pytest
from ra.dsl import APISuite, Autotest


class TestAutotest:
    def test_genscope(self, test_raml):
        raml = test_raml('simple')
        api = APISuite(raml, app=None)
        autotest = Autotest(api)

        name, scope = autotest._genscope('/users', api.raml.resources['/users'])

        assert name == 'users'
        resource_scope = api.resource_scopes[0]
        assert resource_scope.scope_fn == scope

