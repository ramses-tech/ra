import collections
import webob
import ramlfications
from functools import wraps


def api(raml):
    return API(raml)


class API(object):
    def __init__(self, raml):
        self.raml = raml
        self.spec = ramlfications.parse(raml)
        self.autotester = None

    def __call__(self, scope_or_route, **request_options):
        """Use instance as a decorator on a function to mark it as a Ra
        test suite (sugar for ``API.suite``).

        Example::

            @ra.api(raml)               # <-- equiv to @ra.API(raml).suite ...
            def suite(api):
                isinstance(api, ra.API) # true
                @api.test('GET /')
                def get_root(req): ...
        """
        return self.suite(scope_or_route)

    def suite(self, scope):
        scope.__ra__ = _RaInfo(scope, api=self, test_suite=True)
        return scope

    def test(self, route, **options):
        def decorator(fn):
            fn.__ra__ = _RaInfo(fn, test=RequestSignature.from_route(
                route, **options))
            return fn
        return decorator

    @property
    def autotest(self):
        if self.autotester is None:
            self.autotester = self.AutoTest()
        return self.autotester

    class AutoTest(object):
        def __init__(self, api):
            self.api = api
            self.hooks = Hooks()

        def __call__(self, app):
            # TODO: implement autotest
            pass


class Hooks(object):
    """Simple hooks manager.

    Hook callbacks run in the order they're added to each hook name, unless
    the word 'before' is in the hook name, in which case they run in reverse
    order so you can wrap things properly.

    Example usage::

        hooks = Hooks()
        @hooks.before
        def fn(x): print(x)

        hooks.after(fn)

        # later ...
        hooks.run('before', 'running before the thing')
        do_the_thing()
        hooks.run('after', 'running after the thing')
    """

    def __init__(self):
        self._hooks = defaultdict(list)

    def run(self, name, *args, **kwargs):
        callbacks = self._hooks[name]
        for callback in callbacks:
            callback(*args, **kwargs)

    def _add_callback(self, name, fn):
        if 'before' in name:
            self._hooks[name] = [fn].extend(self._hooks[name])
        else:
            self._hooks[name].append(fn)

    def __getattr__(self, name):
        "Use as a decorator to add callbacks to hook ``name``"
        return functools.partial(self._add_callback, name)


class RequestSignature(object):
    """Stores request signature (URL, method and options) used when
    declaring tests.
    """
    def __init__(self, url, method='GET', **options):
        self.url = url
        self.method = method
        self.options = options

    @classmethod
    def from_route(cls, route, **options):
        method, url = route.split()[:2]
        return cls(url, method, **options)

    def make_request(self, app, **options):
        """Given a webtest-like ``app``, can generate a ``ra.Request`` using
        ``request_signature.make_request(app)``.
        """
        status = options.pop('status', None)
        expect_errors = options.pop('expect_errors', None)

        _request = app.RequestClass.blank(
            self.url, method=self.method, **self.options)
        request = Request(_request)

        @request.execute_with
        def execute_request():
            return app.do_request(
                _request, status=status, expect_errors=expect_errors)

        return request


class Request(object):
    """A wrapper for webob/webtest-like requests that can be injected with
    an "execute" function, and called as a function to execute.

    Designed to be passed a function that's a closure over a webtest-like app,
    where the app executes the request. Example::

        app = get_webtest_like_app()
        _request = app.RequestClass.blank('/cats', method='POST')
        request = Request(_request)

        @request.execute_with
        def execute_fn():
            app.do_request(_request)
        response = request()
    """
    def __init__(self, request_to_wrap):
        self._wrapped = request_to_wrap
        self._execute_fn = None

    def __getattr__(self, attr):
        return getaattr(self.wrapped, attr)

    def execute_with(self, fn):
        self._execute_fn = fn
        return fn

    def __call__(self):
        if self._execute_fn is None:
            raise NotImplementedError("_execute_fn not set; aborting")
        return self._execute_fn()


#TODO: maybe use attrs
class _RaInfo(object):
    "Internal tagging object for storing info on __ra__ attribute"

    def __init__(self, object, api=None, test=None, test_suite=False):
        self.object = object
        self.api = api
        self.test = test
        self.test_suite = test_suite

    def issuite(self):
        return self.test_suite

    def __repr__(self):
        return str(self.__dict__)
