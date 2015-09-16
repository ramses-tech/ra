class Examples(object):
    def __init__(self):
        self.factories = {}

    def make_factory(self, resource_name, example):
        def factory(**params):
            if not example:
                return {}
            obj = example.copy()
            obj.update(params)
            return obj
        self.factories[resource_name] = factory

    def get_factory(self, resource_name):
        return self.factories[resource_name]

    def build(self, resource_name, **kwargs):
        return self.factories[resource_name](**kwargs)
