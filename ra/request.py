import fnmatch
import simplejson as json
import webtest
from .utils import listify
from .validate import RAMLValidator


def make_request_class(app, base=None):
    """Create a callable, app-bound request class from a base request class.

    Request objects built from this class are passed to test functions.
    The request object is callable with this signature:

        req(validate=True, **req_params)

    When called, a request is made against app, passing the object as
    the request to send, applying any additional request parameters passed.
    It also takes a ``validate`` keyword to determine if RAML validation
    assertions should be automatically made on the response before
    returning it (default is True).

    The request object expects to be assigned a ``raml`` attribute with
    the ra.raml.ResourceNode to validate against as the value.

    :param app:         the app we want to make requests to, generally an
                        instance of ``webtest.TestApp`` but can be anything
                        that responds to request() taking a webob-like request
                        object as a first positional argument, and accepts
                        request parameters as keyword args.
    :param base:        the base request class
                        (default ``webtest.TestRequest``).

    :return:    a new class for callable requests bound to :app: and pre-set
                with :req_params:
    """
    if base is None:
        base = webtest.TestRequest

    ResponseClass = getattr(base, 'ResponseClass', webtest.TestResponse)

    def __call__(self, validate=True, **req_params):
        resp = app.request(self, **req_params)
        if validate:
            RAMLValidator(resp, self.raml).validate(validate)
        return resp

    def encode_data(self, JSONEncoder=None):
        if JSONEncoder is None:
            JSONEncoder = self.JSONEncoder
        import codecs
        self.body = codecs.encode(json.dumps(self.data, cls=JSONEncoder),
                                  'utf-8')

    def match(self, only=None, exclude=None):
        """Returns True if this request's method and path match conditions.

        Conditions are strings or lists of strings of the form 'METHOD /path'.
        Either method or path can be omitted to match solely on the other.

        If :only: is provided, request must match at least one of the provided
        strings.

        If :exclude: is provided, request must not match any of the provided
        strings.
        """
        # using self.scope.path because we want to match on the path
        # before uri_params are filled or base_uri is prepended
        return _match_request(self.scope.path, self.method, only, exclude)

    RequestClass = type(
        'Request',
        (base,),
        {
            'data': None,
            'factory': None,
            'raml': None,
            'scope': None,
            'JSONEncoder': None,
            '__call__': __call__,
            'encode_data': encode_data,
            'match': match,
            'ResponseClass': ResponseClass
        })

    return RequestClass


def _match_request(path, method, only=None, exclude=None):
    only, exclude = listify(only), listify(exclude)

    if only:
        if not any(_condition_match(pattern, method, path)
                   for pattern in only):
            return False
    if exclude:
        if any(_condition_match(pattern, method, path)
               for pattern in exclude):
            return False
    return True


def _condition_match(pattern, method, path):
    """Check if method and path of request match condition pattern.
    """
    if ' ' in pattern:
        pmethod, ppath = pattern.split(' ', 1)
    elif pattern.startswith('/'):
        pmethod, ppath = None, pattern
    else:
        pmethod, ppath = pattern, None

    if pmethod:
        if pmethod.upper() != method.upper():
            return False

    if ppath:
        if not fnmatch.fnmatch(path, ppath):
            return False

    return True
