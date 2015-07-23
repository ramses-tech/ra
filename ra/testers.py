from .raml_utils import (
    get_response_by_code,
    get_schema_by_mediatype,
)
from .base import TesterBase


class ResourceTester(TesterBase):
    _request_func = None

    def __init__(self, resource, testapp):
        super(ResourceTester, self).__init__()
        self.resource = resource
        self.testapp = testapp

    def __repr__(self):
        return 'Resource({}, {})'.format(
            self.resource.method,
            self.resource.path)

    @property
    def request(self, *args, **kwargs):
        if self._request_func is None:
            http_method = self.resource.method.lower()
            self._request_func = getattr(
                self, '_request_{}'.format(http_method))
        return self._request_func

    def _request_get(self, *args, **kwargs):
        return self.testapp.get(
            self.resource.absolute_uri, *args, **kwargs)

    def test_body(self, response):
        raml_resp = get_response_by_code(
            self.resource, response.status_code)
        if raml_resp is None:
            self.log_skip('Test response body')
            self.save_error('No response body specified for status '
                            'code {}'.format(response.status_code))
            return

        media_type = 'application/json'
        schema = get_schema_by_mediatype(raml_resp, media_type)
        if schema is None:
            self.log_skip('Test response body')
            self.save_error('No body schema specified for content type '
                            '{} and status code {}'.format(
                                media_type, response.status_code))
            return

        self.log_ok('Test response body')

    def test(self):
        response = self.request()
        self.test_body(response)


class RAMLTester(TesterBase):
    _raml_root = None
    _testapp = None

    def __init__(self, wsgi_app, raml_path):
        super(RAMLTester, self).__init__()
        self.wsgi_app = wsgi_app
        self.raml_path = raml_path

    def __repr__(self):
        return str(self.raml_root)

    @property
    def raml_root(self):
        if self._raml_root is None:
            import ramlfications
            self._raml_root = ramlfications.parse(self.raml_path)
        return self._raml_root

    @property
    def testapp(self):
        if self._testapp is None:
            from webtest import TestApp
            self._testapp = TestApp(self.wsgi_app)
        return self._testapp

    def test_resources(self):
        self.output('\nTesting resources:')
        for resource in self.raml_root.resources:

            # DEBUG
            if resource.method.lower() != 'get' or '{' in resource.path:
                continue

            tester = ResourceTester(resource, self.testapp)
            tester.test()
            self.merge_errors(tester)

    def test(self):
        self.test_resources()
        self.show_errors()
