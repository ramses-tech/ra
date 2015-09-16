import random
import re
from string import ascii_letters


def path_from_uri(uri):
    return STRIP_PROTOCOL_HOST_PORT.sub('', uri).rstrip('/')


STRIP_PROTOCOL_HOST_PORT = re.compile(r'^(?:\w+://)?[^/]*')
def path_from_uri(uri):
    return STRIP_PROTOCOL_HOST_PORT.sub('', uri).rstrip('/')


def list_to_dict(lst, by='name'):
    dct = {}
    for el in (lst or []):
        dct[getattr(el, by)] = el
    return dct


def get_uri_param_name(url):
    "Get the name of the last URI template parameter"
    part = url.strip('/').split('{')[-1]
    part = part.split('}')[0]
    return part.strip()


def merge_query_params(url, params):
    """Takes a :url:, potentially with a querystring, and :params:,
    a dict of new querystring parameters, and merges the querystring
    parameters, returning a 2-tuple of a clean url and a separated
    querystring.
    """
    qs = str('')
    if params:
        if not isinstance(params, six.string_types):
            params = urlencode(params, doseq=True)
            if str('?') in url:
                url += str('&')
            else:
                url += str('?')
            url += params
        if str('?') in url:
            url, qs = url.split(str('?'), 1)
    return url, qs


INVALID_IDENTIFIER_CHARS = re.compile(r'[^a-zA-Z_]+')
def path_to_identifier(path):
    "Convert a URI path to a valid python identifier"
    return INVALID_IDENTIFIER_CHARS.sub('_', path).strip('_')
