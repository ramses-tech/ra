from pyramid.config import Configurator
from ramses import registry


@registry.add
def encrypt(event):
    """ Crypt :new_value: if it's not crypted yet """
    import cryptacular.bcrypt
    field = event.field
    new_value = field.new_value
    min_length = field.params['min_length']
    if len(new_value) < min_length:
        raise ValueError(
            '`{}`: Value length must be more than {}'.format(
                field.name, field.params['min_length']))

    crypt = cryptacular.bcrypt.BCRYPTPasswordManager()
    if new_value and not crypt.match(new_value):
        encrypted = str(crypt.encode(new_value))
        field.new_value = encrypted
        event.set_field_value(encrypted)


@registry.add
def lowercase(event):
    """ Make :new_value: lowercase (and stripped) """
    value = (event.field.new_value or '').lower().strip()
    event.set_field_value(value)


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include('ramses')
    return config.make_wsgi_app()
