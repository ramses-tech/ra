def get_response_by_code(resource, code):
    responses = resource.responses or []
    for resp in responses:
        if resp.code == code:
            return resp


def get_body_by_mediatype(raml_obj, mediatype):
    bodies = raml_obj.body or []
    for body in bodies:
        if body.mime_type == mediatype:
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
