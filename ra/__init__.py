import re
import collections
import webob
import ramlfications
import six
import simplejson as json
from functools import wraps, partial

from .utils import get_uri_param_name
from .raml_utils import get_body_by_media_type


STRIP_PROTOCOL_HOST_PORT = re.compile(r'^(?:\w+://)?[^/]*')


def api(raml, app):
    """The main entry point to using Ra.

    :return: instance of ra.API
    """
    return API(raml, app)


class API(object):
    def __init__(self, raml_path_or_string, app, JSONEncoder=None):
        self.app = app
        self.test_suite = TestSuite()

        if not raml_path_or_string.startswith('#%RAML'):
            self.raml_path = raml_path_or_string
        else:
            self.raml_path = None

        self.raml = ramlfications.parse(raml_path_or_string)
        self.raml_resource_nodes = sort_resources(self.raml.resources)

        self.path_prefix = STRIP_PROTOCOL_HOST_PORT.sub(
            '', self.raml.base_uri).rstrip('/')

        self.resources = []

        self.RequestClass = make_request_class(app)

        # if JSONEncoder is None:
        #     # try to get JSONEncoder from app (like webtest.TestApp)
        #     JSONEncoder = getattr(app, 'JSONEncoder', json.JSONEncoder)
        self.JSONEncoder = JSONEncoder

    def resource(self, path, factory=None, parent=None, **uri_params):
        full_path = resource_full_path(path, parent)
        if full_path not in self.raml_resource_nodes:
            raise APIError("Trying to declare resource scope {}: resource not "
                           "defined in RAML: {}".format(path, self.raml_path))

        res = list(self.raml_resource_nodes[full_path].values())[0]
        uri_args = uri_args_from_example(res)
        uri_args.update(uri_params)

        resource = Resource(path, self,
                            factory=factory, parent=parent, **uri_args)
        self.resources.append(resource)

        def decorator(fn):
            # tag this function as a resource scope for the pytest collector
            # and store the argument that will be passed to it when it's called
            fn.__ra__ = {
                'type': 'resource',
                'args': [resource],
                'path': full_path
            }
            fn.__test__ = False # this is a scope for tests, not a test
            return fn

        return decorator


class Resource(object):
    def __init__(self, path, api, factory=None, parent=None, **uri_params):
        self.path = resource_full_path(path, parent)
        self.name = resource_name_from_path(path)
        self.api = api
        self.app = api.app
        self.parent = parent
        self._factory = factory
        self.methods = dict()

        RequestClass = self.api.RequestClass
        # if it looks like a webob request class, treat it like one
        self._request_factory = (RequestClass.blank
                                if getattr(RequestClass, 'blank', None)
                                else RequestClass)

        self.uri_params = {}
        if parent is not None:
            self.uri_params = parent.uri_params
        self.uri_params.update(uri_params)

    @property
    def full_path(self):
        return self.api.path_prefix + self.path

    @property
    def is_dynamic(self):
        return self.path.strip('/').endswith('}')

    def resolve_path(self, **uri_params):
        args = self.uri_params.copy()
        args.update(uri_params)
        return self.full_path.format(**args)

    @property
    def resolved_path(self):
        return self.resolve_path()

    @property
    def factory(self):
        """Default resource factory"""
        if self._factory is not None:
            return self._factory

        if self.is_dynamic:
            if self.parent is not None:
                return self.parent.factory
            else:
                return None

        try:
            post_resource = self.api.raml_resource_nodes[self.path]['POST']
        except KeyError:
            return None
        else:
            body =  get_body_by_media_type(post_resource,
                                           'application/json')
            self._factory = lambda: body.example
            return self._factory

    def resource(self, path, factory=None, **uri_params):
        """Declare a scope for a subresource of this resource.
        """
        return self.api.resource(path, factory=factory, parent=self,
                                 **uri_params)

    def _get_method_node(self, verb):
        return self.api.raml_resource_nodes[self.path][verb.upper()]

    def method_test(self, verb, test_fn=None, **req_params):
        verb = verb.upper()
        # XXX: hard-coded default content type, probably ok for now
        content_type = req_params.pop('content_type', 'application/json')

        try:
            method_node = self._get_method_node(verb)
        except KeyError:
            raise APIError("Tried to add test for undeclared method "
                           "{} on {}".format(verb, self.path))

        method = Method(method_node)

        factory = req_params.pop('factory', None)
        data = req_params.pop('data', None)
        body = req_params.get('body', None)

        if body is None:
            if data is None:
                factory = factory or method.factory or self.factory or None

                if factory is not None:
                    data = factory()

            if data is not None:
                body = six.binary_type(json.dumps(data), encoding='utf-8') # , cls=self.api.JSONEncoder) # XXX

        self.methods[verb] = method

        def decorator(fn):
            req = self._request_factory(self.resolved_path,
                                        method=verb,
                                        body=body,
                                       content_type='application/json',
                                       **req_params)

            req.data = data
            req.factory = factory
            req.raml = method.resource_node

            # force the first parameter to be a request object.
            # XXX: this doesn't work with pytest because it won't recognize
            # a partial object as a test function (it doesn't have a code
            # object)
            # fn = partial(fn, req)
            #
            # Instead we should use fixtures for pytest.

            # pytest collector will see this tag and recognize the function
            # as a test function. The 'req' item will be returned by the
            # 'req' fixture.
            fn.__ra__ = { 'type': 'test', 'method': method, 'req': req }

            # name_qualifiers = ' '.join(fn.__name__.split('_')[1:])
            # if name_qualifiers:
            #     name_qualifiers = ' ' + name_qualifiers
            # test_wrapper.__name__ = "{} {}{}".format(
            #     verb, self.path, name_qualifiers)

            # XXX: this might not be necessary, at least for pytest, but
            # might be to support other frameworks.
            #
            # It also would be necessary if we want autotests to be overridden.
            self.api.test_suite.add_test(fn)
            method.add_test(fn)

            return fn

        if six.callable(test_fn):
            return decorator(test_fn)
        return decorator

    def get(self, test_fn=None, **req_params):
        return self.method_test('get', test_fn=test_fn, **req_params)

    def post(self, test_fn=None, **req_params):
        return self.method_test('post', test_fn=test_fn, **req_params)

    def put(self, test_fn=None, **req_params):
        return self.method_test('put', test_fn=test_fn, **req_params)

    def patch(self, test_fn=None, **req_params):
        return self.method_test('patch', test_fn=test_fn, **req_params)

    def delete(self, test_fn=None, **req_params):
        return self.method_test('delete', test_fn=test_fn, **req_params)

    def head(self, test_fn=None, **req_params):
        return self.method_test('head', test_fn=test_fn, **req_params)

    def options(self, test_fn=None, **req_params):
        return self.method_test('options', test_fn=test_fn, **req_params)


class Method(object):
    def __init__(self, resource_node):
        self.resource_node = resource_node
        self.tests = []

    @property
    def factory(self):
        body = get_body_by_media_type(self.resource_node, 'application/json')
        if body is None:
            return None
        return lambda: body.example

    def add_test(self, test):
        self.tests.append(test)

    def __getattr__(self, name):
        attr = getattr(self.resource_node, name, None)
        if attr is not None:
            return attr
        raise AttributeError


class TestSuite(object):
    def __init__(self):
        self.tests = []

    def add_test(self, test):
        self.tests.append(test)


def resource_name_from_path(path):
    return path.split('/')[-1]


def sort_resources(resources):
    resources_by_path = collections.OrderedDict()

    for resource in resources:
        method = resource.method.upper()

        resources_by_path.setdefault(resource.path, collections.OrderedDict())
        resources_by_path[resource.path].setdefault(method, [])
        resources_by_path[resource.path][method] = resource

    for methods in six.itervalues(resources_by_path):
        if 'delete' in methods:
            methods.move_to_end('delete')

    return resources_by_path


def uri_args_from_example(resource_node):
    if resource_node.uri_params is None:
        return {}
    params = {}
    for param in resource_node.uri_params:
        params[param.name] = param.example
    return params


def resource_full_path(path, parent=None):
    if parent is None:
        return path
    return parent.path + path


def fields_in_string(s):
    import string
    return [tup[1] for tup in string.Formatter().parse(s)]


def safe_format(s, *args, **kwargs):
    """Safe version of str.format() that doesn't die with extra args."""
    fieldnames = fields_in_string(s)
    argc = len(args)
    actual_pos_args = 0
    actual_kw_args = {}
    for name in fieldnames:
        if name:
            actual_kw_args[name] = kwargs[name]
        else:
            actual_pos_args += 1
    return s.format(*args[:actual_pos_args], **actual_kw_args)



def make_request_class(app, base=None):
    """Create a callable, app-bound request class from a base request class.

    :param app: the app we want to make requests to, generally an instance of
                ``webtest.TestApp`` but can be anything that responds to
                request() and takes a webob-like request object as a first
                positional argument.
    :param base: the base request class (default ``webob.request.BaseRequest``).
    :return: a new callable request class bound to :app:
    """


    try:
        from webtest import TestResponse
    except ImportError: # pragma: no cover
        ResponseClass = base or webob.Response
    else: # pragma: no cover
        ResponseClass = TestResponse

    def __call__(self, status=None, expect_errors=False, **req_params):
        return app.request(self,
                           status=status, expect_errors=expect_errors,
                          **req_params)

    RequestClass = type(
        'Request',
        (webob.request.BaseRequest,),
        {
            '__call__': __call__,
            'ResponseClass': ResponseClass
        })

    return RequestClass


class APIError(Exception): pass
