class Examples(object):
    def __init__(self):
        self.factories = {}

    def make_factory(self, resource_name, example):
        self.factories[resource_name] = lambda: example

    def get_factory(self, resource_name):
        return self.factories[resource_name]

    def build(self, resource_name, **kwargs):
        return self.factories[resource_name](**kwargs)
