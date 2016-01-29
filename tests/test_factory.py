import pytest
from ra import factory


class TestExamples:
    @pytest.fixture
    def examples(self):
        return factory.Examples()

    @pytest.fixture
    def an_example(self):
        return { 'a': 1, 'b': 2 }

    def test_make_and_get_factory(self, examples, an_example):
        examples.make_factory('test', an_example)
        factory = examples.get_factory('test')
        assert factory() == an_example

    def test_factory_params(self, examples, an_example):
        examples.make_factory('test', an_example)
        factory = examples.get_factory('test')
        obj = factory(c=3)
        assert obj['c'] == 3

    def test_build(self, examples, an_example):
        examples.make_factory('test', an_example)
        factory = examples.get_factory('test')
        obj = examples.build('test', c=4)
        assert obj['a'] == 1
        assert obj['c'] == 4
