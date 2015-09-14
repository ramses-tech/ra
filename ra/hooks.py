import collections
import functools


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

