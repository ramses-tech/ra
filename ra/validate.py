import jsonschema
from .raml import named_params_to_json_schema


class RAMLValidator(object):
    def __init__(self, response, raml):
        self.response = response
        self.raml = raml
        self.raml_response = raml.responses.get(response.status_code)

    def validate(self, validate=["headers", "body"]):
        if self.raml is None:
            raise ValueError("Trying to validate with no RAML ResourceNode")
        if validate == True or "headers" in validate:
            self.validate_headers()
        if validate == True or "body" in validate:
            self.validate_body()

    def validate_body(self):
        try:
            schema = self.raml_response.body['application/json'].schema
        except (AttributeError, KeyError):
            return # RAML response bodies are optional

        jsonschema.validate(self.response.json, schema)

    def validate_headers(self):
        try:
            raml_headers_node = self.raml_response.headers
        except AttributeError:
            return # RAML headers are optional
        else:
            raml_headers_raw = list(self.raml_response.headers.values())

        raml_headers = {header.name: dict(header.raw[header.name])
                        for header in raml_headers_raw}
        http_headers = dict(self.response.headers)

        for name, data in raml_headers.items():
            self._validate_header(data, http_headers.get(name))

    def _validate_header(self, header_props, header_val):
        try:
            prop_schema = named_params_to_json_schema(header_props)
        except KeyError as ex:
            raise RAMLValidationError('Missing required RAML named parameter: '
                                      '{}'.format(ex))
        try:
            header_val = _convert_type(prop_schema['type'], header_val)
        except ValueError:
            raise RAMLValidationError('Header value is not of type '
                                      '`{}`'.format(prop_schema['type']))

        required = prop_schema.pop('required', False)
        json_schema = {
            '$schema': 'http://json-schema.org/draft-04/schema',
            'type': 'object',
            'properties': {
                'header': prop_schema
            },
        }
        if required:
            json_schema['required'] = ['header']
        header = {} if header_val is None else {'header': header_val}
        jsonschema.validate(header, json_schema)


def _convert_type(type_, value):
    booleans = {'true': True, 'false': False}
    if type_ == 'number':
        return float(value)
    elif type_ == 'integer':
        return int(value)
    elif type_ == 'boolean':
        return booleans.get(value, value)
    return value


class RAMLValidationError(object): pass
