import imp
import sys
import types
import pytest
from _pytest.python import PyCollector, Module

from ..dsl import APISuite


"""pytest plugin for Ra.

Large amounts of code stolen from `pytest-describe
<http://github.com/ropez/pytest-describe>`_.
"""


def trace_function(funcobj, *args, **kwargs):
    """Call a function, and return its locals"""
    funclocals = {}

    def _tracefunc(frame, event, arg):
        # Activate local trace for first call only
        if frame.f_back.f_locals.get('_tracefunc') == _tracefunc:
            if event == 'return':
                funclocals.update(frame.f_locals.copy())

    sys.setprofile(_tracefunc)
    try:
        funcobj(*args, **kwargs)
    finally:
        sys.setprofile(None)

    return funclocals


def make_module_from_function(funcobj):
    """Evaluates the local scope of a function, as if it was a module"""
    module = imp.new_module(funcobj.__name__)
    scope = _ra_attr(funcobj, 'scope')
    funclocals = trace_function(funcobj, scope)
    module.__dict__.update(funclocals)
    return module


def copy_markinfo(module, funcobj):
    from _pytest.mark import MarkInfo

    marks = {}
    for name, val in funcobj.__dict__.items():
        if isinstance(val, MarkInfo):
            marks[name] = val

    for obj in module.__dict__.values():
        if isinstance(obj, types.FunctionType):
            for name, mark in marks.items():
                setattr(obj, name, mark)


def merge_pytestmark(module, parentobj):
    try:
        pytestmark = parentobj.pytestmark
        if not isinstance(pytestmark, list):
            pytestmark = [pytestmark]
        try:
            if isinstance(module.pytestmark, list):
                pytestmark.extend(module.pytestmark)
            else:
                pytestmark.append(module.pytestmark)
        except AttributeError:
            pass
        module.pytestmark = pytestmark
    except AttributeError:
        pass


def add_hooks_to_module(module):
    @pytest.fixture(autouse=True, scope='module')
    def scope_around_all(request, req):
        scope = _ra_attr(req.module, 'scope')
        @request.addfinalizer
        def fin():
            scope.hooks.run('after_all')
        scope.hooks.run('before_all')

    @pytest.fixture(autouse=True, scope='function')
    def scope_around_each(request, req):
        scope = _ra_attr(req.module, 'scope')
        @request.addfinalizer
        def fin():
            scope.hooks.run('after_each', req)
        scope.hooks.run('before_each', req)


class ResourceScopeCollector(PyCollector):
    def __init__(self, funcobj, parent):
        super(ResourceScopeCollector, self).__init__(funcobj.__name__, parent)
        self.funcobj = funcobj

    def collect(self):
        self.session._fixturemanager.parsefactories(self)
        return super(ResourceScopeCollector, self).collect()

    def _getobj(self):
        return self._memoizedcall('_obj', self._importtestmodule)

    def _makeid(self):
        """Magic that makes fixtures local to each scope"""
        return self.parent.nodeid + '::' + self.funcobj.__name__

    def _importtestmodule(self):
        """Import a ra test suite function scope as if it was a module"""
        module = make_module_from_function(self.funcobj)
        copy_markinfo(module, self.funcobj)
        merge_pytestmark(module, self.parent.obj)
        return module

    def funcnamefilter(self, name):
        """Treat all nested functions as tests, without requiring the 'test_'
        prefix, unless they begin with an underscore.

        Functions marked as pytest fixtures should already be ignored.
        """
        return not name.startswith('_')

    def classnamefilter(self, name):
        """Don't allow test classes"""
        return False

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__,
                                repr(self.funcobj.__name__))


class AutotestCollector(PyCollector):
    def __init__(self, module, parent):
        super(AutotestCollector, self).__init__(module.__name__+'.py', parent)
        self._module = module

    def collect(self):
        self.session._fixturemanager.parsefactories(self)
        return super(AutotestCollector, self).collect()

    def _getobj(self):
        return self._module

    def funcnamefilter(self, name):
        """Treat all nested functions as tests, without requiring the 'test_'
        prefix, unless they begin with an underscore.

        Functions marked as pytest fixtures should already be ignored.
        """
        return not name.startswith('_')

    def classnamefilter(self, name):
        """Don't allow test classes"""
        return False

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__,
                                repr(self._module.__name__))


def pytest_pycollect_makeitem(__multicall__, collector, name, obj):
    if isinstance(obj, types.FunctionType):
        if _ra_attr(obj, 'type')  == 'resource':
            return ResourceScopeCollector(obj, collector)
        elif _ra_attr(obj, 'type') == 'autotest':
            return AutotestCollector(obj(), collector)

    return __multicall__.execute()


def _ra_attr(obj, name):
    return getattr(obj, '__ra__', {}).get(name, None)


@pytest.fixture
def req(request):
    return _ra_attr(request.function, 'req')


@pytest.fixture(autouse=True, scope='session')
def api_around_all(request):
    @request.addfinalizer
    def fin():
        for api in APISuite.instances:
            api.hooks.run('after_all')
    for api in APISuite.instances:
        api.hooks.run('before_all')


@pytest.fixture(autouse=True, scope='function')
def api_before_each(request, req):
    @request.addfinalizer
    def fin():
        for api in APISuite.instances:
            if req.scope.api is api:
                api.hooks.run('after_each', req)
    for api in APISuite.instances:
        if req.scope.api is api:
            api.hooks.run('before_each', req)

