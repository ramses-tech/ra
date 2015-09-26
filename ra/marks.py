class Mark(dict):
    pass


def _dict(obj):
    """Work with obj.__dict__ or obj if it doesn't have one (it should be one).
    This lets us pass in regular objects or their dicts (like f_locals).
    """
    return getattr(obj, '__dict__', obj)

def mark(obj, **attrs):
    """Creates ``__ra__`` marker dict of :obj: with :attrs: as attributes"""
    _dict(obj)['__ra__'] = Mark(**attrs)


def get(obj, name, default=None):
    "Get attribute :name: stored in the ``__ra__`` marker dict of :obj:"
    _mark = _dict(obj).get('__ra__', Mark())
    return _mark.get(name, default)


def set(obj, name, value):
    """Set attribute :name: stored in the ``__ra__`` marker dict of :obj:
    to :value:"""
    _mark = _dict(obj).get('__ra__', None)
    if _mark is None:
        _dict(obj)['__ra__'] = _mark = Mark()
    _mark[name] = value
