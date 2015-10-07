from pyramid.config import Configurator
from ramses import registry


@registry.add
def encrypt(**kwargs):
    """ Crypt :new_value: if it's not crypted yet """
    import cryptacular.bcrypt
    new_value = kwargs['new_value']
    field = kwargs['field']
    min_length = field.params['min_length']
    if len(new_value) < min_length:
        raise ValueError(
            '`{}`: Value length must be more than {}'.format(
                field.name, field.params['min_length']))

    crypt = cryptacular.bcrypt.BCRYPTPasswordManager()
    if new_value and not crypt.match(new_value):
        new_value = str(crypt.encode(new_value))
    return new_value


@registry.add
def lowercase(**kwargs):
    """ Make :new_value: lowercase (and stripped) """
    return (kwargs['new_value'] or '').lower().strip()


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include('ramses')
    return config.make_wsgi_app()
