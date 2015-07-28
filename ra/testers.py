from jsonschema import validate as jschema_validate
from six.moves import urllib

from .raml_utils import (
    get_response_by_code,
    get_body_by_mediatype,
    named_params_schema,
    get_query_params,
)
from .utils import (
    RandomValueGenerator,
)
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
            supported_methods = [
                'get', 'post', 'patch', 'put', 'head', 'options',
                'delete'
            ]
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
    _required_params = None

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
            self._request_body = None if body is None else body.example
        return self._request_body

    @property
    def required_params(self):
        if self._required_params is None:
            raml_params = get_query_params(
                self.resource, required_only=True)
            self._required_params = {
                param.name: RandomValueGenerator.generate_value(param)
                for param in raml_params}
        return self._required_params

    def make_url(self, params=None, add_required=True):
        if params is None:
            params = {}
        if add_required:
            params.update(self.required_params)

        if params:
            # http://stackoverflow.com/a/2506477
            url_parts = list(urllib.parse.urlparse(
                self.resource.absolute_uri))
            query = dict(urllib.parse.parse_qsl(url_parts[4]))
            query.update(params)
            url_parts[4] = urllib.parse.urlencode(query)
            return urllib.parse.urlunparse(url_parts)

        return self.resource.absolute_uri

    def _get_request(self, url=None, **kwargs):
        if url is None:
            url = self.make_url()
        return self.testapp.get(url, **kwargs)

    def _head_request(self, url=None, **kwargs):
        if url is None:
            url = self.make_url()
        return self.testapp.head(url, **kwargs)

    def _options_request(self, url=None, **kwargs):
        if url is None:
            url = self.make_url()
        return self.testapp.options(url, **kwargs)

    def _create_update_request(self, url, method, **kwargs):
        if url is None:
            url = self.make_url()
        if self.request_body is None:
            raise Exception('Request body example is not specified.')
        meth = getattr(self.testapp, '{}_json'.format(method))
        return meth(url, params=self.request_body, **kwargs)

    def _post_request(self, url=None, **kwargs):
        return self._create_update_request(url, 'post', **kwargs)

    def _patch_request(self, url=None, **kwargs):
        return self._create_update_request(url, 'patch', **kwargs)

    def _put_request(self, url=None, **kwargs):
        return self._create_update_request(url, 'put', **kwargs)

    def _delete_request(self, url=None, **kwargs):
        if url is None:
            url = self.make_url()
        params = self.request_body or {}
        return self.testapp.delete_json(url, params=params, **kwargs)


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

    def _run_common_tests(self, body=True, headers=True, query_string=True):
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
            if body:
                self.test_body(response, raml_response)
            if headers:
                self.test_headers(response, raml_response)

        if query_string:
            self.test_query_params()
        return response

    def _run_get_tests(self):
        self._run_common_tests()

    def _run_head_tests(self):
        self._run_common_tests(body=False)

    def _run_options_tests(self):
        self._run_common_tests(body=False)

    def _run_post_tests(self):
        self._run_common_tests()

    def _run_patch_tests(self):
        self._run_common_tests()

    def _run_put_tests(self):
        self._run_common_tests()

    def _run_delete_tests(self):
        self._run_common_tests()

    def test(self):
        func_name = '_run_{}_tests'.format(self.resource.method.lower())
        test_func = getattr(self, func_name)
        test_func()


class QueryParamsTester(ResourceRequestMixin, ResourceTesterBase):
    def test_response_code(self, qs_params, valid_codes, step_name):
        url = self.make_url(qs_params)
        step_name = '{}: {}'.format(
            step_name, urllib.parse.urlsplit(url).query)
        try:
            response = self.request(url=url)
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
            # Skip required query string params because they are already
            # present in url and were tested by simple request
            if param.required:
                continue
            value = RandomValueGenerator.generate_value(param)
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
            local_step = step_name + ': ' + name
            try:
                self.test_header(data, http_headers.get(name))
            except Exception as ex:
                self.output_fail(local_step)
                self.save_fail('{}: `{}`:\n{}'.format(
                    local_step, name, str(ex)))
            else:
                self.output_ok(local_step)
