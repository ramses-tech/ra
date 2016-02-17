import imp
import sys
import types
import pytest
from _pytest.python import PyCollector, Module

from ..dsl import APISuite
from .. import marks


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
    scope = marks.get(funcobj, 'scope')
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


class ResourceScopeCollector(PyCollector):
    def __init__(self, funcobj, parent):
        super(ResourceScopeCollector, self).__init__(funcobj.__name__, parent)
        self.funcobj = funcobj

    def _reorder_collected(self, data):
        """ Move DELETE http method test to the end of all tests.
        """
        priority = {
            'post':     1,
            'get':      2,
            'put':      2,
            'patch':    2,
            'head':     2,
            'options':  2,
            'delete':   3,
        }
        data = sorted(
            data,
            key=lambda x: priority.get(getattr(x, 'name', ''), 4))
        return data

    def collect(self):
        self.session._fixturemanager.parsefactories(self)
        results = super(ResourceScopeCollector, self).collect()
        results = self._reorder_collected(results)
        return results

    def _getobj(self):
        return self._memoizedcall('_obj', self._importtestmodule)

    def _makeid(self):
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
        super(AutotestCollector, self).__init__(module.__name__, parent)
        self._module = module

    def _reorder_collected(self, data):
        """ Move item route tests after collection route tests. """
        data_dict = {getattr(res, 'name', ''): res for res in data}
        for name, res in data_dict.items():
            if '}' in name:
                data.remove(res)
                data.append(res)
        return data

    def collect(self):
        self.session._fixturemanager.parsefactories(self)
        results = super(AutotestCollector, self).collect()
        results = self._reorder_collected(results)
        return results

    def _getobj(self):
        return self._module

    def _makeid(self):
        return self.parent.nodeid + '::' + self._module.__name__

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


def pytest_pycollect_makeitem(collector, name, obj):
    if isinstance(obj, types.FunctionType):
        if marks.get(obj, 'type')  == 'resource':
            return ResourceScopeCollector(obj, collector)
    elif isinstance(obj, marks.Mark):
        autotest = obj.get('autotest')
        if autotest:
            return AutotestCollector(autotest, collector)


@pytest.fixture
def req(request):
    return marks.get(request.function, 'req')


@pytest.fixture
def api(req):
    return req.scope.api


@pytest.fixture
def examples(api):
    return api.examples


@pytest.fixture
def app(api):
    return api.app
