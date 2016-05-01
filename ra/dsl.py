import os
import warnings
import six
import simplejson as json
import webtest

from . import raml, marks
from .factory import Examples
from .request import make_request_class
from .utils import (
    path_from_uri,
    merge_query_params,
    path_to_identifier,
    caller_scope,
    guess_rootdir,
)


class APISuite(object):
    """Represents an API test suite.
    """

    def __init__(self, raml_path_or_string, app='config:test.ini',
                 relative_to=None, JSONEncoder=None):
        """Instantiates an API test suite for the given :raml: and :app:."""

        if relative_to is None:
            relative_to = guess_rootdir()

        if isinstance(app, webtest.TestApp):
            app = app
        else:
            app = webtest.TestApp(app, relative_to=relative_to)
        self.app = app

        if not raml.is_raml(raml_path_or_string):
            raml_path_or_string = os.path.normpath(
                os.path.join(relative_to, raml_path_or_string))

        self.raml_path, self.raml = _parse_raml(raml_path_or_string)
        self.path_prefix = path_from_uri(self.raml.base_uri)
        self.resource_scopes = []

        self.test_suite = TestSuite()

        self.RequestClass = make_request_class(app)

        self.JSONEncoder = JSONEncoder or json.JSONEncoder

        self.examples = self._define_factories()

    def _define_factories(self):
        """Create factories for example body values.

        Returns an instance of ``ra.factory.Examples`` with factories
        stored for each route with an example declared. The POST body
        factory for each collection is also keyed by resource name,
        e.g. "POST /users/{username}/profile" is also keyed as "user.profile".
        """
        examples = Examples()
        for path, nodes in six.iteritems(self.raml.resources):
            for method, node in six.iteritems(nodes):
                try:
                    example = node.body['application/json'].example
                except KeyError:
                    continue
                else:
                    route = "{} {}".format(method, path)
                    examples.make_factory(route, example)
                    if method == 'POST':
                        resource_name = raml.resource_name_from_path(path)
                        examples.make_factory(resource_name, example)
        return examples

    def resource(self, path, factory=None, parent=None, **uri_params):
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
        :param parent:      parent ResourceScope, default None
        :param uri_params:  kw args are used to fill in URI parameters in the
                            path (by default, the uri_params example value from
                            the RAML is used)
        """
        # pop parent arg passed in by the subresource decorator
        full_path = raml.resource_full_path(path, parent)

        if full_path in self.raml.resources:
            # get URI param example values:
            res = list(self.raml.resources[full_path].values())[0]
            uri_args = raml.uri_args_from_example(res)
            uri_args.update(uri_params)
        else:
            warnings.warn("Declaring resource scope {}: resource not declared "
                          "in RAML ({})".format(full_path, self.raml_path))
            uri_args = uri_params

        def decorator(fn):
            scope = ResourceScope(fn, path, self,
                                  factory=factory, parent=parent,
                                  **uri_args)
            self.resource_scopes.append(scope)

            # tag this function as a resource scope for the pytest collector
            # and store the argument that will be passed to it when it's called
            marks.mark(fn, type='resource', scope=scope, path=full_path)
            fn.__test__ = False # this is a scope for tests, not a test
            fn.__name__ = full_path

            return fn

        return decorator

    def autotest(self, override=False, settings=None):
        autotest_module = Autotest(
            self,
            override=override,
            settings=settings,
        ).generate()
        marks.set(caller_scope(), 'autotest', autotest_module)

    def __repr__(self):
        return '{}("{}", app={})'.format(
            self.__class__.__name__, self.raml_path, repr(self.app))



class ResourceScope(object):
    """Represents a resource scope that contains tests for methods on the
    resource, as well as nested resource scopes.

    Resource scopes derive a path to make requests against for the resource,
    including resolving URI parameters. They also provide factories for
    generating data for request bodies.
    """
    def __init__(self, scope_fn, path, api,
                 factory=None, parent=None, **uri_params):
        self.scope_fn = scope_fn
        self.path = raml.resource_full_path(path, parent)
        self.name = raml.resource_name_from_path(self.path)
        self.api = api
        self.app = api.app
        self.factory = factory
        self.raml_methods = self.api.raml.resources[self.path]
        self.uri_params = uri_params

        RequestClass = self.api.RequestClass
        # if it looks like a webob request class, treat it like one
        self._request_factory = (RequestClass.blank
                                if getattr(RequestClass, 'blank', None)
                                else RequestClass)

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
                            body string, or ``factory`` to pass a factory to
                            use to create the body data for this test.  You
                            can also use ``query_params`` to pass
                            querystring parameters as a dict.
        """
        verb = verb.upper()
        content_type = req_params.pop('content_type', 'application/json')

        try:
            method = self.raml_methods[verb]
        except KeyError:
            warnings.warn("Tried to add test for undeclared method "
                          "{} on {} (RAML={})".format(verb, self.path,
                                                      self.api.raml_path))

        factory = req_params.pop('factory', None)
        data = req_params.pop('data', None)
        body = req_params.get('body', None)
        query_params = req_params.get('query_params', {})

        if body is None:
            if data is None:
                examples = self.api.examples
                factory = (factory or
                           self.factory or
                           examples.get_factory(' '.join([verb, self.path])) or
                           examples.get_factory(self.name) or
                           None)

                if factory is not None:
                    data = factory()

        url, query_string = merge_query_params(self.resolved_path,
                                               query_params or {})

        if not query_string:
            query_string = req_params.pop(query_string, '')

        def decorator(fn):
            req = self._request_factory(url,
                                        method=verb,
                                        query_string=query_string,
                                        content_type='application/json',
                                        **req_params)

            req.factory = factory
            req.data = data
            req.body = body
            req.JSONEncoder = self.api.JSONEncoder

            if body is None:
                req.encode_data()

            req.raml = method
            req.scope = self

            # pytest collector will see this tag and recognize the function
            # as a test function. The 'req' item will be returned by the
            # 'req' fixture.
            marks.mark(fn, type='test', req=req)

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
    """Used internally to log when tests are added for a resource.
    """
    def __init__(self):
        self.tests = []

    def add_test(self, test, resource_node):
        self.tests.append((test, resource_node))

    def test_exists(self, method, path):
        for test, resource_node in self.tests:
            if resource_node.method == method and resource_node.path == path:
                return True
        return False


def _parse_raml(raml_path_or_string):
    "Returns the RAML file path (or None if arg is a string) and parsed RAML."
    raml_path = '<str>'
    if not raml.is_raml(raml_path_or_string):
        raml_path = raml_path_or_string

    parsed_raml = raml.parse(raml_path_or_string)

    return raml_path, parsed_raml


class Autotest(object):
    def __init__(self, api, override=False, settings=None):
        if settings is None:
            settings = {}
        self.settings = settings
        self.api = api
        self.resources = api.raml.resources
        self.test_suite = api.test_suite
        self.override = override

    def generate(self):
        scopes = dict(self._genscope(path, methods, override=self.override)
                      for path, methods in six.iteritems(self.resources))
        import imp
        module = imp.new_module("autotests")
        module.__dict__.update(scopes)
        return module

    def _genscope(self, path, methods, override=False):
        @self.api.resource(path)
        def _autoresource(resource):
            for method in methods:
                if override and self.test_suite.test_exists(method, path):
                    continue
                method = method.lower()

                @getattr(resource, method)
                def test(req):
                    req()
                    from time import sleep
                    sleep(self.settings.get('postrequest_sleep', 0.5))
                test.__name__ = method
                import inspect
                inspect.currentframe().f_locals[method] = test
                del test

        return (path_to_identifier(path), _autoresource)
