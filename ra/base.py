import logging
from logging import INFO, ERROR, DEBUG

import six

from .utils import Colors


class TesterBase(object):
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('ra')
        self.fails = []
        self.skips = []
        super(TesterBase, self).__init__(*args, **kwargs)

    def save_fail(self, err_message):
        self.fails.append('{}: {}'.format(self, err_message))

    def save_skip(self, err_message):
        self.skips.append('{}: {}'.format(self, err_message))

    def log(self, message, level=INFO):
        self.logger.log(level, message)

    def print_(self, message):
        six.print_(message)

    def output(self, message, level=INFO):
        self.log(message, level)
        self.print_(message)

    def output_ok(self, message):
        message = str(self) + ': ' + message
        self.log(message + '... OK')
        self.print_(message + '... ' + Colors.green('OK'))

    def output_skip(self, message):
        message = str(self) + ': ' + message
        self.log(message + '... SKIP', level=DEBUG)
        self.print_(message + '... ' + Colors.yellow('SKIP'))

    def output_fail(self, message):
        message = str(self) + ': ' + message
        self.log(message + '... FAIL', level=ERROR)
        self.print_(message + '... ' + Colors.red('FAIL'))

    def merge_errors(self, tester):
        self.fails += tester.fails

    def merge_skips(self, tester):
        self.skips += tester.skips

    def merge_reports(self, tester):
        self.merge_errors(tester)
        self.merge_skips(tester)

    def show_fails(self):
        if self.fails:
            self.output(Colors.red('\n\nFails:'), level=ERROR)
            for message in self.fails:
                self.output('-'*50)
                self.output(message, level=ERROR)

    def show_skips(self):
        if self.skips:
            self.output(Colors.yellow('\n\nSkips:'), level=ERROR)
            for message in self.skips:
                self.output('-'*50)
                self.output(message, level=DEBUG)

    def show_report(self):
        self.show_fails()
        self.show_skips()
        if self.fails:
            raise Exception('{} tests have failed'.format(
                len(self.fails)))

    def test(self):
        raise NotImplementedError
