import six
import re


STRIP_DYNAMIC = re.compile(r'/\{.*?}')


def is_raml(s):
    return s.startswith("#%RAML")


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


## XXX: clean up after this:


def get_response_by_code(resource, code):
    responses = resource.responses or []
    for resp in responses:
        if resp.code == code:
            return resp


def get_body_by_media_type(method, media_type):
    bodies = method.body or []
    for body in bodies:
        if body.mime_type == media_type:
            return body


def get_query_params(resource, required_only=False):
    query_params = resource.query_params or []
    if required_only:
        query_params = [param for param in query_params
                        if param.required]
    return query_params


def get_uri_param(resource, name):
    uri_params = resource.uri_params or []
    for param in uri_params:
        if param.name == name:
            return param


def get_resource_siblings(resource):
    """ Get siblings of :resource:.

    :param resource: Instance of ramlfications.raml.ResourceNode.
    """
    path = resource.path
    return [res for res in resource.root.resources
            if res.path == path]


def is_dynamic_uri(uri):
    """ Determine whether `uri` is a dynamic uri or not.

    Assumes a dynamic uri is one that ends with '}' which is a Pyramid
    way to define dynamic parts in uri.

    :param uri: URI as a string.
    """
    return uri.strip('/').endswith('}')


def is_dynamic_resource(raml_resource):
    """ Determine if :raml_resource: is a dynamic resource.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    """
    return raml_resource and is_dynamic_uri(raml_resource.path)


def get_static_parent(raml_resource, method=None):
    """ Get static parent resource of :raml_resource: with HTTP
    method :method:.

    :param raml_resource:Instance of ramlfications.raml.ResourceNode.
    :param method: HTTP method name which matching static resource
        must have.
    """
    parent = raml_resource.parent
    while is_dynamic_resource(parent):
        parent = parent.parent

    if parent is None:
        return parent

    match_method = method is not None
    if match_method:
        if parent.method.upper() == method.upper():
            return parent
    else:
        return parent

    for res in parent.root.resources:
        if res.path == parent.path:
            if res.method.upper() == method.upper():
                return res


def named_params_schema(params):
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
