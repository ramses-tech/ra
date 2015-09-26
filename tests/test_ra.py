

def test_api(mocker, test_raml):
    import ra
    raml = test_raml('simple')
    app = mocker.Mock()
    api = ra.api(raml, app)
    assert isinstance(api, ra.dsl.APISuite)
