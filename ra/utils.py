import random
from string import ascii_letters


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


class RandomValueGenerator(object):
    def __init__(self, params):
        self.params = dict(params)
        super(RandomValueGenerator, self).__init__()

    @classmethod
    def generate_value(cls, param):
        if 'example' in param.raw:
            return param.raw['example']
        else:
            generator = cls(param.raw)
            return generator()

    def _random_string(self):
        if 'enum' in self.params:
            return random.choice(self.params['enum'])
        min_length = self.params.get('minLength', 1)
        max_length = self.params.get('maxLength', 15)
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
    part = url.strip('/').split('{')[-1]
    part = part.split('}')[0]
    return part.strip()


def get_part_by_schema(url, schema):
    schema_parts = schema.split('/')
    url_parts = url.split('/')
    for index, part in enumerate(schema_parts):
        if part.startswith('{') and part.endswith('}'):
            return url_parts[index]


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
