"""
This module provides a parse function for parsing RAML with ramlfications,
as well as wrapper classes for the main ramlfications types to make
them more pleasant to work with.
"""
import collections
import re
import six
import ramlfications
import wrapt
from .utils import list_to_dict


def parse(raml_path_or_string):
    root = ramlfications.parse(raml_path_or_string)
    return RootNode(root)


def is_raml(s):
    return s.startswith("#%RAML")


STRIP_DYNAMIC = re.compile(r'/\{.*?}')

def resource_name_from_path(path, singularize=True):
    """Returns a (possibly nested) resource name for an API path).

    This function will try to treat collection and item paths the same,
    singularizing the collection name if singularize=True (default).
    Nested resources on the item are appended to make a dotted name
    for the subresource.

    For example, both "/users" and "/users/{username}" return 'user',
    while '/users/{username}/profile' returns 'user.profile'.

    Attribute resources like "/users/{username}/settings" will return
    'user.settings' despite not being model object (it's treated the same
    by Ra).
    """
    parts = STRIP_DYNAMIC.sub('', path.strip('/')).split('/')
    if singularize:
        import inflection
        parts = (inflection.singularize(part) for part in parts)
    return '.'.join(parts)


def uri_args_from_example(resource_node):
    """Recursively determine example values for any URI args
    in the resource path.
    """
    uri_args = {}
    if resource_node.parent:
        uri_args = uri_args_from_example(resource_node.parent)

    if resource_node.uri_params is None:
        return uri_args

    for name, param in six.iteritems(resource_node.uri_params):
        uri_args[name] = param.example

    return uri_args


def resource_full_path(path, parent=None):
    if parent is None:
        return path
    return parent.path + path


def named_params_to_json_schema(params):
    """ Convert RAML "named parameters" to JSON schema params.

    Only params that participate in JSON schema validation
    are translated.

    Does not support:
        type: file
    """
    schema = {'type': params['type']}

    if schema['type'] == 'date':
        schema['type'] = 'string'
        if 'pattern' not in params:
            schema['format'] = 'date-time'

    optional = ('enum', 'minLength', 'maxLength', 'minimum',
                'maximum', 'required', 'pattern', 'default')

    for param in optional:
        if param in params:
            schema[param] = params[param]

    return schema


class RootNode(wrapt.ObjectProxy):
    "Wraps a ``ramlfications.raml.RootNode and its contained objects``"
    def __init__(self, wrapped):
        super(RootNode, self).__init__(wrapped)

        self.resources = _map_resources(ResourceNode(r)
                                       for r in wrapped.resources)


class ResourceNode(wrapt.ObjectProxy):
    """Wraps a ``ramlfications.raml.ResourceNode`` to map parameters, bodies and
    responses by a sensible key.
    """
    def __init__(self, wrapped):
        super(ResourceNode, self).__init__(wrapped)

        self.query_params     =  list_to_dict(wrapped.query_params, by='name')
        self.uri_params       =  list_to_dict(wrapped.uri_params, by='name')
        self.base_uri_params  =  list_to_dict(wrapped.base_uri_params, by='name')
        self.form_params      =  list_to_dict(wrapped.form_params, by='name')
        self.headers          =  list_to_dict(wrapped.headers, by='name')
        self.body             =  list_to_dict(wrapped.body, by='mime_type')
        self.responses        =  list_to_dict((Response(r) for r
                                               in (wrapped.responses or [])),
                                               by='code')


class Response(wrapt.ObjectProxy):
    """Wraps a ``ramlfications.raml.Response`` to map headers and body by
    a sensible key."""
    def __init__(self, wrapped):
        super(Response, self).__init__(wrapped)

        self.headers = list_to_dict(wrapped.headers, by='name')
        self.body    = list_to_dict(wrapped.body, by='mime_type')


def _map_resources(resources):
    """Map resources by path and then by method, preserving order except for
    moving DELETEs to the end."""

    resources_by_path = collections.OrderedDict()

    for resource in resources:
        method = resource.method.upper()

        resources_by_path.setdefault(resource.path, collections.OrderedDict())
        resources_by_path[resource.path].setdefault(method, [])
        resources_by_path[resource.path][method] = resource

    return resources_by_path
