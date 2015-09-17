import collections
import functools
import fnmatch


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
        self._hooks = collections.defaultdict(list)

    def run(self, name, node=None):
        """Run callbacks for hook :name:.

        :param name: hook name
        :param node: expects a resource_node (or any object with method
                     and path attributes for the current test)
        """
        callbacks = self._hooks[name]

        for callback, conditions in callbacks:
            only, exclude = conditions['only'], conditions['exclude']

            if only:
                if node is None:
                    continue
                else:
                    ok = False
                    for pattern in only:
                        if _condition_match(pattern, node.method, node.path):
                            ok = True
                            break
                    if not ok:
                        continue
            if exclude:
                if node is not None:
                    ok = True
                    for pattern in exclude:
                        if _condition_match(pattern, node.method, node.path):
                            ok = False
                            break
                    if not ok:
                        continue
            callback()

    def _add_callback(self, name, fn=None, only=None, exclude=None):
        def decorator(_fn):
            item = (_fn, dict(only=only, exclude=exclude))
            self._hooks[name].append(item)
            return _fn
        if fn is not None:
            return decorator(fn)
        return decorator

    def __getattr__(self, name):
        "Use as a decorator to add callbacks to hook ``name``"
        return functools.partial(self._add_callback, name)


def _condition_match(pattern, method, path):
    """Check if method and path of request match condition pattern.
    """
    if ' ' in pattern:
        pmethod, ppath = pattern.split(' ', 1)
    elif pattern.startswith('/'):
        pmethod, ppath = None, pattern
    else:
        pmethod, ppath = pattern, None

    if pmethod:
        if pmethod.upper() != method.upper():
            return False

    if ppath:
        if not fnmatch.fnmatch(path, ppath):
            return False

    return True
