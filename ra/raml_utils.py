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
