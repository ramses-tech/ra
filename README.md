# ra

Ra is a test suite generator and helper library for testing APIs described
by [RAML](http://raml.org/) documents.

Out of the box, Ra provides a basic, automated test suite to test the routes
declared in the RAML document. It provides test helpers for augmenting these
with custom tests to test application-specific logic, side effects, etc.

Ra is primarily designed to provide testing support for
[ramses](http://github.com/brandicted/ramses) and
[nefertari](http://github.com/brandicted/nefertari) applications, but can
be used with any WSGI-conformant, RAML-described API.

It currently depends on pytest but may be adapted for other test frameworks
in the future. It works best using WebTest but doesn't require it.

## Name

Ra was the god of the sun, the most important god in ancient Egypt.


## Try it (dev)

```bash
    $ pip install -r requirements.txt
    $ cd tests/apps/ramses_test
    $ py.test
```

See the docs in `docs/`, and the `api.raml` and `tests/test_api.py` in
`tests/apps/ramses_test`

