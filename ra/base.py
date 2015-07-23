import logging
from logging import INFO, ERROR, DEBUG

import six


log = logging.getLogger('ra')


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


class TesterBase(object):
    def __init__(self, *args, **kwargs):
        self.errors = []
        super(TesterBase, self).__init__(*args, **kwargs)

    def save_error(self, err_message):
        self.errors.append('{}: {}'.format(self, err_message))

    def log(self, message, level=INFO):
        log.log(level, message)

    def print_(self, message):
        six.print_(message)

    def output(self, message, level=INFO):
        self.log(message, level)
        self.print_(message)

    def log_ok(self, message):
        message = str(self) + ': ' + message
        self.log(message + ' OK')
        self.print_(message + '... ' + Colors.green('OK'))

    def log_skip(self, message):
        message = str(self) + ': ' + message
        self.log(message + ' SKIP', level=DEBUG)
        self.print_(message + '... ' + Colors.yellow('SKIP'))

    def log_fail(self, message):
        message = str(self) + ': ' + message
        self.log(message + ' FAIL', level=ERROR)
        self.print_(message + '... ' + Colors.red('FAIL'))

    def merge_errors(self, tester):
        self.errors += tester.errors

    def show_errors(self):
        self.output(Colors.red('\nErrors:'), level=ERROR)
        for error in self.errors:
            self.output(error, level=ERROR)

    def test(self):
        raise NotImplementedError
