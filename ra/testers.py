from jsonschema import validate as jschema_validate

from .raml_utils import (
    get_response_by_code,
    get_schema_by_mediatype,
    named_params_schema,
)
from .base import TesterBase


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
            self.merge_reports(tester)

    def test(self):
        self.test_resources()
        self.show_report()


class ResourceTesterBase(TesterBase):
    def __init__(self, resource):
        super(ResourceTesterBase, self).__init__()
        self.resource = resource

    def __repr__(self):
        return 'Resource({}, {})'.format(
            self.resource.method,
            self.resource.path)


class ResourceTester(ResourceTesterBase):
    _request_func = None

    def __init__(self, resource, testapp):
        super(ResourceTester, self).__init__(resource)
        self.testapp = testapp

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

    def test_body(self, response, raml_response):
        tester = ResponseBodyTester(self.resource, raml_response, response)
        tester.test()
        self.merge_reports(tester)

    def test_headers(self, response, raml_response):
        tester = ResponseHeadersTester(
            self.resource, raml_response, response)
        tester.test()
        self.merge_reports(tester)

    def test(self):
        response = self.request()
        raml_response = get_response_by_code(
            self.resource, response.status_code)
        if raml_response is None:
            self.output_skip('Test resource')
            self.save_skip('Test resource: No response specified for '
                           'status code {}'.format(response.status_code))
        else:
            self.test_body(response, raml_response)
            self.test_headers(response, raml_response)


class ResponseBodyTester(ResourceTesterBase):
    def __init__(self, resource, raml_response, response):
        super(ResponseBodyTester, self).__init__(resource)
        self.raml_response = raml_response
        self.response = response

    def test(self):
        self.test_schema()

    def test_schema(self):
        step_name = 'Test response body schema'
        media_type = 'application/json'
        schema = get_schema_by_mediatype(self.raml_response, media_type)
        if schema is None:
            self.output_skip(step_name)
            self.save_skip(
                '{}: No body schema specified for content type '
                '{} and status code {}'.format(
                    step_name, media_type, self.response.status_code))
            return

        try:
            jschema_validate(self.response.json, schema)
        except Exception as ex:
            self.output_fail(step_name)
            self.save_fail('{}: {}'.format(step_name, str(ex)))
        else:
            self.output_ok(step_name)


class ResponseHeadersTester(ResourceTesterBase):
    def __init__(self, resource, raml_response, response):
        super(ResponseHeadersTester, self).__init__(resource)
        self.raml_response = raml_response
        self.response = response

    def _convert_type(self, type_, value):
        booleans = {'true': True, 'false': False}
        if type_ == 'number':
            return float(value)
        elif type_ == 'integer':
            return int(value)
        elif type_ == 'boolean':
            return booleans.get(value, value)
        return value

    def test_header(self, header_props, header_val):
        try:
            prop_schema = named_params_schema(header_props)
        except KeyError as ex:
            raise Exception('Missing required RAML named parameter: '
                            '{}'.format(ex))

        try:
            header_val = self._convert_type(prop_schema['type'], header_val)
        except ValueError:
            raise Exception('Header value is not of type `{}`'.format(
                prop_schema['type']))

        json_schema = {
            'id': 'headerValidationSchema',
            '$schema': 'http://json-schema.org/draft-03/schema',
            'type': 'object',
            'properties': {'header': prop_schema}
        }
        header = {} if header_val is None else {'header': header_val}
        jschema_validate(header, json_schema)

    def test(self):
        step_name = 'Test headers'
        raml_headers_raw = self.raml_response.headers or []
        raml_headers = {header.name: dict(header.raw[header.name])
                        for header in raml_headers_raw}
        if not raml_headers:
            self.output_skip(step_name)
            self.save_skip('{}: No response HTTP headers specified'.format(
                step_name))
            return

        http_headers = dict(self.response.headers)
        for name, data in raml_headers.items():
            try:
                self.test_header(data, http_headers.get(name))
            except Exception as ex:
                self.output_fail(step_name)
                self.save_fail('{}: `{}`: {}'.format(
                    step_name, name, str(ex)))
            else:
                self.output_ok(step_name)
