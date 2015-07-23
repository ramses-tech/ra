from webtest import TestApp


class Tester(object):
    def __init__(self, wsgi_app, raml_path):
        self.wsgi_app = wsgi_app
        self.raml_path = raml_path

    def _init_webtest_app(self):
        self.app = TestApp(self.wsgi_app)

    def run(self):
        self._init_webtest_app()
