class Examples(object):
    def __init__(self):
        self.factories = {}

    def make_factory(self, resource_name, example):
        def factory(**params):
            if not example:
                return {}
            try:
                obj = example.copy()
                obj.update(params)
            except AttributeError:
                raise ValueError("example failed to parse as JSON:\n\n"
                                 "{}".format(example))
            return obj
        self.factories[resource_name] = factory

    def get_factory(self, resource_name):
        return self.factories.get(resource_name)

    def build(self, resource_name, **kwargs):
        return self.factories[resource_name](**kwargs)


# XXX: unused now, but should maybe use it as a helper for
# defining custom factories
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
