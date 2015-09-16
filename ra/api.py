import warnings
import webob
import six
import simplejson as json

from . import raml
from .raml_utils import (
    is_raml,
    resource_name_from_path,
    uri_args_from_example,
    resource_full_path,
)
from . import factory
from .utils import path_from_uri
from .hooks import Hooks


class API(object):
    """Represents an API test suite.
    """
    instances = []

    def __new__(cls, *args, **kwargs):
        instance = super(API, cls).__new__(cls)
        cls.instances.append(instance)
        return instance

    def __init__(self, raml_path_or_string, app, JSONEncoder=None):
        """Instantiates an API test suite for the given RAML and app.
        """
        self.app = app
        self.test_suite = TestSuite()

        self.raml_path, self.raml = _parse_raml(raml_path_or_string)
        self.path_prefix = path_from_uri(self.raml.base_uri)
        self.resource_scopes = []

        self.RequestClass = make_request_class(app)

        self.JSONEncoder = JSONEncoder or json.JSONEncoder

        self.hooks = Hooks()
        self.examples = self._define_factories()

    def _define_factories(self):
        examples = factory.Examples()
        for resources in six.itervalues(self.raml.resources):
            try:
                post_resource = resources['POST']
                example = post_resource.body['application/json'].example
            except KeyError:
                pass
            else:
                resource_name = resource_name_from_path(post_resource.path)
                examples.define_factory(resource_name, lambda: example)
        return examples

    def resource(self, path, factory=None, **uri_params):
        """Decorator for declaring a resource scope.

        Tests defined within the resource scope apply to that resource,
        and resource scopes can be nested within resource scopes. The
        nesting of resource scopes can match that of the RAML definition,
        though it's not required.

        Fixtures defined in a resource scope are local to that scope;
        they behave essentially like a module scope.

        :param path:        the resource path segment.
        :param factory:     factory callable for generating data for the
                            request body. The data will be JSON-encoded when
                            the request is made. The default factory uses
                            the example body from the RAML.
        :param uri_params:  kw args are used to fill in URI parameters in the
                            path (by default, the uri_params example value from
                            the RAML is used)
        """
        # pop parent arg passed in by the subresource decorator
        parent = uri_params.pop('parent', None)
        full_path = resource_full_path(path, parent)

        if full_path in self.raml.resources:
            # get URI param example values:
            res = list(self.raml.resources[full_path].values())[0]
            uri_args = uri_args_from_example(res)
            uri_args.update(uri_params)
        else:
            warnings.warn("Declaring resource scope {}: resource not declared "
                          "in RAML ({})".format(full_path, self.raml_path))

        scope = ResourceScope(path, self,
                              factory=factory, parent=parent,
                              **uri_args)
        self.resource_scopes.append(scope)

        def decorator(fn):
            # tag this function as a resource scope for the pytest collector
            # and store the argument that will be passed to it when it's called
            fn.__ra__ = {
                'type': 'resource',
                'scope': scope,
                'path': full_path
            }
            fn.__test__ = False # this is a scope for tests, not a test
            return fn

        return decorator


class ResourceScope(object):
    """Represents a resource scope that contains tests for methods on the
    resource, as well as nested resource scopes.

    Resource scopes derive a path to make requests against for the resource,
    including resolving URI parameters. They also provide factories for
    generating data for request bodies.
    """
    def __init__(self, path, api, factory=None, parent=None, **uri_params):
        self.path = resource_full_path(path, parent)
        self.name = resource_name_from_path(path)
        self.api = api
        self.app = api.app
        self.parent = parent
        self._factory = factory
        self.raml_methods = self.api.raml.resources[self.path]

        RequestClass = self.api.RequestClass
        # if it looks like a webob request class, treat it like one
        self._request_factory = (RequestClass.blank
                                if getattr(RequestClass, 'blank', None)
                                else RequestClass)

        self.uri_params = {}
        if parent is not None:
            self.uri_params = parent.uri_params
        self.uri_params.update(uri_params)

        self.hooks = Hooks()

    @property
    def full_path(self):
        "Return the full path, including any prefix in the API's base_uri"
        return self.api.path_prefix + self.path

    @property
    def is_dynamic(self):
        """Returns true if the resource is dynamic (ending with a URI param).

        For example: "/users/{username}" is a dynamic resource
        """
        return self.path.strip('/').endswith('}')

    def resolve_path(self, **uri_params):
        """Resolve any URI parameters in resource.full_path with given
        URI parameter values.

        Uses the URI parameter keyword args passed when instantiating this
        resource scope, which can be overridden by passing new values here.
        Unspecified URI param values try to find their value in the RAML
        example property.
        """
        args = self.uri_params.copy()
        args.update(uri_params)
        return self.full_path.format(**args)

    @property
    def resolved_path(self):
        "Shortcut to resolve_path called with no arguments."
        return self.resolve_path()

    @property
    def factory(self):
        """Returns the default resource factory for generating request body
        data.

        The default factory looks for the example body property in the RAML
        definition for the POST method on this resource (or in the case of
        a dynamic resource, this resource's static parent which represents
        the collection).

        For example, for either a "/users" or a "/users/{username}" resource,
        this will look for the POST body example value on "/users".
        """
        if self.is_dynamic:
            if self.parent is None:
                return None
            else:
                return self.parent.factory

        return self.api.examples.get_factory(self.name)

    def resource(self, path, factory=None, **uri_params):
        """Declare a nested resource scope under this resource scope.
        """
        return self.api.resource(path, factory=factory, parent=self,
                                 **uri_params)

    def method(self, verb, test_fn=None, **req_params):
        """Generic method for defining a test, mostly used internally.

        If called without ``test_fn``, a decorator is returned.

        The specific method decorators (ResourceScope.get, .post, ...) are
        more convenient in most cases.

        :param verb:        HTTP method verb ("get", "post", ...)
        :param test_fn:     the test function
        :param req_params:  any parameters passed here will be passed to the
                            request object when the request is made (e.g.
                            ``headers``, ``content_type``, etc). You can use
                            the ``data`` keyword to pass request body data
                            that should be encoded, or ``body`` to pass a raw
                            body string.
        """
        verb = verb.upper()
        content_type = req_params.pop('content_type', 'application/json')

        try:
            method = self.raml_methods[verb]
        except KeyError:
            warnings.warn("Tried to add test for undeclared method "
                          "{} on {} (RAML={}".format(verb, self.path,
                                                     self.api.raml_path))

        factory = req_params.pop('factory', None)
        data = req_params.pop('data', None)
        body = req_params.get('body', None)

        if body is None:
            if data is None:
                factory = (factory or
                           (method.example_factory if method else None) or
                           self.factory or
                           None)

                if factory is not None:
                    data = factory()

            if data is not None:
                body = six.binary_type(
                    json.dumps(data, cls=self.api.JSONEncoder),
                    encoding='utf-8')

        def decorator(fn):
            req = self._request_factory(self.resolved_path,
                                        method=verb,
                                        body=body,
                                       content_type='application/json',
                                       **req_params)

            req.data = data
            req.factory = factory
            req.raml = method
            req.scope = self

            # pytest collector will see this tag and recognize the function
            # as a test function. The 'req' item will be returned by the
            # 'req' fixture.
            fn.__ra__ = { 'type': 'test', 'req': req }

            self.api.test_suite.add_test(fn, method)

            return fn

        if six.callable(test_fn):
            return decorator(test_fn)
        return decorator

    def get(self, test_fn=None, **req_params):
        """Decorator for defining GET method tests.

        Can be used with or without arguments.  If called with keyword
        arguments, they are treated as request parameters and applied
        to the request when it's executed.

        :param test_fn:     pass this to use directly as a decorator
        :param req_params:  parameters applied to the request
        """
        return self.method('get', test_fn=test_fn, **req_params)

    def post(self, test_fn=None, **req_params):
        "Decorator for defining POST method tests, like ``ResourceScope.get``"
        return self.method('post', test_fn=test_fn, **req_params)

    def put(self, test_fn=None, **req_params):
        "Decorator for defining PUT method tests, like ``ResourceScope.get``"
        return self.method('put', test_fn=test_fn, **req_params)

    def patch(self, test_fn=None, **req_params):
        "Decorator for defining PATCH method tests, like ``ResourceScope.get``"
        return self.method('patch', test_fn=test_fn, **req_params)

    def delete(self, test_fn=None, **req_params):
        "Decorator for defining DELETE method tests, like ``ResourceScope.get``"
        return self.method('delete', test_fn=test_fn, **req_params)

    def head(self, test_fn=None, **req_params):
        "Decorator for defining HEAD method tests, like ``ResourceScope.get``"
        return self.method('head', test_fn=test_fn, **req_params)

    def options(self, test_fn=None, **req_params):
        "Decorator for defining OPTIONS method tests, like ``ResourceScope.get``"
        return self.method('options', test_fn=test_fn, **req_params)


class TestSuite(object):
    """Used internally to log when tests are added for a method.
    """
    def __init__(self):
        self.tests = []

    def add_test(self, test, method):
        self.tests.append((test, method))


def _parse_raml(raml_path_or_string):
    "Returns the RAML file path (or None if arg is a string) and parsed RAML."
    raml_path = None
    if not is_raml(raml_path_or_string):
        raml_path = raml_path_or_string

    parsed_raml = raml.parse(raml_path_or_string)

    return raml_path, parsed_raml


def make_request_class(app, base=None):
    """Create a callable, app-bound request class from a base request class.

    :param app:     the app we want to make requests to, generally an
                    instance of ``webtest.TestApp`` but can be anything
                    that responds to request() taking a webob-like request
                    object as a first positional argument, and accepts
                    request parameters as keyword args.
    :param base:    the base request class
                    (default ``webob.request.BaseRequest``).

    :return:    a new class for callable requests bound to :app: and pre-set
                with :req_params:
    """


    try:
        from webtest import TestResponse
    except ImportError: # pragma: no cover
        ResponseClass = base or webob.Response
    else: # pragma: no cover
        ResponseClass = TestResponse

    def __call__(self, **req_params):
        return app.request(self, **req_params)

    RequestClass = type(
        'Request',
        (webob.request.BaseRequest,),
        {
            '__call__': __call__,
            'ResponseClass': ResponseClass
        })

    return RequestClass


class APIError(Exception): pass
