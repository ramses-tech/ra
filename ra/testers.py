import six
import logging
from logging import INFO, ERROR, DEBUG


log = logging.getLogger(__name__)


class TesterBase(object):
    def __init__(self, *args, **kwargs):
        self.errors = []
        super(TesterBase, self).__init__(*args, **kwargs)

    def save_error(self, err_message):
        self.errors.append('{}: {}'.format(self, err_message))

    def log(self, message, level=INFO):
        six.print_(message)
        log.log(level, message)

    def log_ok(self, message):
        self.log(message + ' OK')
        six.print_(message + '...\033[92m OK')

    def log_skip(self, message):
        self.log(message + ' SKIP', level=DEBUG)
        six.print_(message + '...\033[93m SKIP')

    def log_fail(self, message):
        self.log(message + ' FAIL', level=ERROR)
        six.print_(message + '...\033[91m FAIL')

    def merge_errors(self, tester):
        self.errors += tester.errors

    def show_errors(self):
        self.log('\nTesting errors:', level=ERROR)
        for error in self.errors:
            self.log(error, level=ERROR)

    def test(self):
        raise NotImplementedError


class ResourceTester(TesterBase):
    def __init__(self, resource, testapp):
        super(ResourceTester, self).__init__()
        self.resource = resource
        self.testapp = testapp

    def __repr__(self):
        return 'Resource ({}, {})'.format(
            self.resource.method,
            self.resource.path)

    def test(self):
        pass


class RAMLTester(TesterBase):
    _raml_root = None
    _testapp = None

    def __init__(self, wsgi_app, raml_path):
        super(RAMLTester, self).__init__()
        self.wsgi_app = wsgi_app
        self.raml_path = raml_path

    def __repr__(self):
        return str(self.raml_root)

    @property
    def raml_root(self):
        if self._raml_root is None:
            import ramlfications
            self._raml_root = ramlfications.parse(self.raml_path)
        return self._raml_root

    @property
    def testapp(self):
        if self._testapp is None:
            from webtest import TestApp
            self._testapp = TestApp(self.wsgi_app)
        return self._testapp

    def test_resources(self):
        self.log('\nTesting resources:')
        for resource in self.raml_root.resources:
            tester = ResourceTester(resource, self.testapp)
            tester.test()
            self.merge_errors(tester)

    def test(self):
        self.test_resources()
        self.show_errors()
