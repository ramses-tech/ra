import os
import pytest


datadir = os.path.abspath(os.path.join(__file__, '..', 'data'))
ramldir = os.path.join(datadir, 'raml')


@pytest.fixture(scope='session')
def test_raml():
    def _test_raml(name, parsed=False):
        ramlpath = os.path.join(ramldir, "{}.raml".format(name))
        if parsed:
            from ra import raml
            return raml.parse(ramlpath)
        else:
            return ramlpath
    return _test_raml
