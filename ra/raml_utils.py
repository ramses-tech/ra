def get_response_by_code(resource, code):
    responses = resource.responses or []
    for resp in responses:
        if resp.code == code:
            return resp


def get_schema_by_mediatype(raml_response, mediatype):
    bodies = raml_response.body or []
    for body in bodies:
        if body.mime_type == mediatype:
            return body.schema


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

    situational = (
        'enum', 'minLength', 'maxLength', 'minimum',
        'maximum', 'required', 'pattern', 'default')

    for param in situational:
        if param in params:
            schema[param] = params[param]

    return schema
