import imp
import sys
import types
import pytest
from _pytest.python import PyCollector

from .. import APIError


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

    args = _ra_attr(funcobj, 'args')
    if args is None:
        raise APIError("Function {} marked with @api.resource should take a "
                       "``resource`` argument")

    funclocals = trace_function(funcobj, *args)
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


class RaResourceCollector(PyCollector):
    def __init__(self, funcobj, parent):
        super(RaResourceCollector, self).__init__(funcobj.__name__, parent)
        self.funcobj = funcobj

    def collect(self):
        self.session._fixturemanager.parsefactories(self)
        return super(RaResourceCollector, self).collect()

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


def pytest_pycollect_makeitem(__multicall__, collector, name, obj):
    if isinstance(obj, types.FunctionType):
        if _ra_attr(obj, 'type')  == 'resource':
            return RaResourceCollector(obj, collector)

    return __multicall__.execute()


def _ra_attr(obj, name):
    return getattr(obj, '__ra__', {}).get(name, None)

@pytest.fixture
def req(request):
    return _ra_attr(request.function, 'req')
