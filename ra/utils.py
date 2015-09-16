import random
import re
from string import ascii_letters


STRIP_PROTOCOL_HOST_PORT = re.compile(r'^(?:\w+://)?[^/]*')


def path_from_uri(uri):
    return STRIP_PROTOCOL_HOST_PORT.sub('', uri).rstrip('/')


def list_to_dict(lst, by='name'):
    dct = {}
    for el in (lst or []):
        dct[getattr(el, by)] = el
    return dct


def path_from_uri(uri):
    return STRIP_PROTOCOL_HOST_PORT.sub('', uri).rstrip('/')


def list_to_dict(lst, by='name'):
    dct = {}
    for el in (lst or []):
        dct[getattr(el, by)] = el
    return dct


# TODO: remove when TestRunners are removed
# just rely on external framework like pytest
class Colors(object):
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

    @classmethod
    def green(cls, msg):
        return cls.GREEN + msg + cls.END

    @classmethod
    def yellow(cls, msg):
        return cls.YELLOW + msg + cls.END

    @classmethod
    def red(cls, msg):
        return cls.RED + msg + cls.END


# TODO: remove
# should just use faker
class RandomValueGenerator(object):
    def __init__(self, params):
        self.params = dict(params)
        super(RandomValueGenerator, self).__init__()

    @classmethod
    def generate_value(cls, params):
        if 'example' in params:
            return params['example']
        else:
            generator = cls(params)
            return generator()

    def _random_string(self):
        if 'enum' in self.params:
            return random.choice(self.params['enum'])
        min_length = self.params.get('minLength', 5)
        max_length = self.params.get('maxLength', 20)
        value_len = random.randint(min_length, max_length)
        letters = [random.choice(ascii_letters)
                   for i in range(value_len)]
        return ''.join(letters)

    def _random_number(self):
        min_val = self.params.get('minimum', 1)
        max_val = self.params.get('maximum', 100) - 1
        val = random.randint(min_val, max_val)
        return val + random.random()

    def _random_integer(self):
        min_val = self.params.get('minimum', 1)
        max_val = self.params.get('maximum', 100)
        return random.randint(min_val, max_val)

    def _random_date(self):
        from datetime import datetime
        return datetime.now().isoformat()

    def _random_boolean(self):
        return random.choice([True, False])

    def _random_array(self):
        return [self._random_string()]

    def _random_object(self):
        return {self._random_string(): self._random_string()}

    def __call__(self):
        type_ = self.params.get('type', 'string')
        func = getattr(self, '_random_{}'.format(type_))
        return func()


def get_uri_param_name(url):
    "Get the name of the last URI template parameter"
    part = url.strip('/').split('{')[-1]
    part = part.split('}')[0]
    return part.strip()


def merge_query_params(url, params):
    """Takes a :url:, potentially with a querystring, and :params:,
    a dict of new querystring parameters, and merges the querystring
    parameters, returning a 2-tuple of a clean url and a separated
    querystring.
    """
    qs = str('')
    if params:
        if not isinstance(params, six.string_types):
            params = urlencode(params, doseq=True)
            if str('?') in url:
                url += str('&')
            else:
                url += str('?')
            url += params
        if str('?') in url:
            url, qs = url.split(str('?'), 1)
    return url, qs


INVALID_IDENTIFIER_CHARS = re.compile(r'[^a-zA-Z_]+')
def path_to_identifier(path):
    "Convert a URI path to a valid python identifier"
    return INVALID_IDENTIFIER_CHARS.sub('_', path).strip('_')


def path_parent(path):
    "Drop the last segment of a path to try to find a parent"
    return '/'.join(path.split('/')[:-1])


# Used by DynamicResourceTester to generate its base url
# by making a POST to the parent resource and checking the
# Location header (url arg) against the resource's uri as
# specified in the RAML (schema arg)
def get_part_by_schema(url, schema):
    schema_parts = schema.split('/')
    url_parts = url.split('/')
    for index, part in enumerate(schema_parts):
        if part.startswith('{') and part.endswith('}'):
            return url_parts[index]


# Used by ResourceRequestMixin to try requests multiple times
def retry(func, args=None, kwargs=None, tries=3, delay=0.5):
    import time
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    for i in range(tries):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            time.sleep(delay)
    raise ex


# TODO: replace RandomValueGenerator with faker
# Used by ResourceRequestMixin to fill required fields using
# RandomValueGenerator
def fill_required_params(data, json_schema):
    data = data.copy()
    required_props = json_schema.get('required', [])
    properties = json_schema.get('properties', {})
    for prop in required_props:
        if prop not in data:
            params = properties.get(prop, {})
            data[prop] = RandomValueGenerator.generate_value(params)
    return data


# Used by RAMLTester to sort resources by method (so that items are
# created, then read/replaced/patched, then deleted)
def sort_by_priority(resources):
    from collections import defaultdict
    priorities = {
        'post': 1,
        'get': 2,
        'head': 3,
        'options': 4,
        'patch': 5,
        'put': 6,
        'delete': 7,
    }
    grouped = defaultdict(list)
    for res in resources:
        grouped[res.path].append(res)
    for path, res_list in grouped.items():
        grouped[path] = sorted(
            res_list, key=lambda x: priorities[x.method.lower()])

    listed = []
    for res in resources:
        if res.path in grouped:
            listed += grouped.pop(res.path)
    return listed
