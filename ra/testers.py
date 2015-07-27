from jsonschema import validate as jschema_validate
from six.moves import urllib

from .raml_utils import (
    get_response_by_code,
    get_body_by_mediatype,
    named_params_schema,
)
from .utils import RandomValueGenerator
from .base import TesterBase


DEFAULT_MEDIA_TYPE = 'application/json'


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
            supported_methods = ['get', 'post']
            method_supported = resource.method.lower() in supported_methods
            is_dynamic = '{' in resource.path
            if not method_supported or is_dynamic:
                continue

            tester = ResourceTester(resource, testapp=self.testapp)
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


class ResourceRequestMixin(object):
    _request_func = None
    _request_body = None

    def __init__(self, *args, **kwargs):
        self.testapp = kwargs.pop('testapp')
        super(ResourceRequestMixin, self).__init__(*args, **kwargs)

    @property
    def request(self, *args, **kwargs):
        if self._request_func is None:
            http_method = self.resource.method.lower()
            self._request_func = getattr(
                self, '_{}_request'.format(http_method))
        return self._request_func

    @property
    def request_body(self, *args, **kwargs):
        if self._request_body is None:
            media_type = DEFAULT_MEDIA_TYPE
            body = get_body_by_mediatype(self.resource, media_type)
            self._request_body = body.example
        return self._request_body

    def _get_request(self, uri=None, **kwargs):
        if uri is None:
            uri = self.resource.absolute_uri
        return self.testapp.get(uri, **kwargs)

    def _post_request(self, uri=None, **kwargs):
        if uri is None:
            uri = self.resource.absolute_uri
        if self.request_body is None:
            raise Exception('Request body example is not specified.')
        return self.testapp.post_json(
            uri, params=self.request_body,
            **kwargs)


class ResourceTester(ResourceRequestMixin, ResourceTesterBase):
    def test_body(self, response, raml_response):
        tester = ResponseBodyTester(self.resource, raml_response, response)
        tester.test()
        self.merge_reports(tester)

    def test_headers(self, response, raml_response):
        tester = ResponseHeadersTester(
            self.resource, raml_response, response)
        tester.test()
        self.merge_reports(tester)

    def test_query_params(self):
        tester = QueryParamsTester(self.resource, testapp=self.testapp)
        tester.test()
        self.merge_reports(tester)

    def _run_common_tests(self):
        """
        Tests:
            * Response body JSON against schema
            * Response headers
            * Requests with query string params
        """
        step_name = 'Resource request'
        try:
            response = self.request()
        except Exception as ex:
            self.output_fail(step_name)
            self.save_fail('{}:\n{}'.format(step_name, str(ex)))
            return

        raml_response = get_response_by_code(
            self.resource, response.status_code)
        if raml_response is None:
            self.output_fail('Test resource')
            self.save_fail(
                'Test resource:\nNot defined response status '
                'code: {}'.format(response.status_code))
        else:
            self.test_body(response, raml_response)
            self.test_headers(response, raml_response)

        self.test_query_params()
        return response

    def _run_get_tests(self):
        self._run_common_tests()

    def _run_post_tests(self):
        self._run_common_tests()

    def test(self):
        func_name = '_run_{}_tests'.format(self.resource.method.lower())
        test_func = getattr(self, func_name)
        test_func()


class QueryParamsTester(ResourceRequestMixin, ResourceTesterBase):
    def test_response_code(self, qs_params, valid_codes, step_name):
        qs_params = urllib.parse.urlencode(qs_params)
        step_name = '{}: {}'.format(step_name, str(qs_params))
        uri = self.resource.absolute_uri + '?' + qs_params
        try:
            response = self.request(uri=uri)
        except Exception as ex:
            self.output_fail(step_name)
            self.save_fail('{}:\n{}'.format(step_name, str(ex)))
        else:
            if response.status_code in valid_codes:
                self.output_ok(step_name)
            else:
                self.output_fail(step_name)
                self.save_fail(
                    '{}:\nNot defined response status code: {}'.format(
                        step_name, response.status_code))

    def test(self):
        step_name = 'Test query params'
        if not self.resource.query_params:
            self.output_skip(step_name)
            self.save_skip(step_name + ': No query params specified')
            return

        valid_codes = [resp.code for resp in self.resource.responses or []]

        for param in self.resource.query_params:
            if 'example' in param.raw:
                value = param.raw['example']
            else:
                generator = RandomValueGenerator(param.raw)
                value = generator()
            self.test_response_code(
                {param.name: value},
                valid_codes, step_name)


class ResponseBodyTester(ResourceTesterBase):
    def __init__(self, resource, raml_response, response):
        super(ResponseBodyTester, self).__init__(resource)
        self.raml_response = raml_response
        self.response = response

    def test(self):
        self.test_schema()

    def test_schema(self):
        step_name = 'Test response body schema'
        media_type = DEFAULT_MEDIA_TYPE
        body = get_body_by_mediatype(self.raml_response, media_type)
        schema = None if body is None else body.schema
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
            self.save_fail('{}:\n{}'.format(step_name, str(ex)))
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
                self.save_fail('{}: `{}`:\n{}'.format(
                    step_name, name, str(ex)))
            else:
                self.output_ok(step_name)
