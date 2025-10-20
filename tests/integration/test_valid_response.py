import pytest
import requests


@pytest.mark.integration
def test_valid_response_error_code_2():

    from fatsecret.fatsecret import AuthenticationError, Fatsecret

    response = requests.Response()
    response._content = b'{"error": {"code": 2, "message": "Authentication required"}}'
    response.status_code = 200
    with pytest.raises(AuthenticationError):
        Fatsecret.valid_response(response)


@pytest.mark.integration
def test_valid_response_error_code_1():

    from fatsecret.fatsecret import Fatsecret, GeneralError

    response = requests.Response()
    response._content = b'{"error": {"code": 1, "message": "General error 1"}}'
    response.status_code = 200
    with pytest.raises(GeneralError):
        Fatsecret.valid_response(response)


@pytest.mark.integration
def test_valid_response_error_code_10():

    from fatsecret.fatsecret import Fatsecret, GeneralError

    response = requests.Response()
    response._content = b'{"error": {"code": 10, "message": "General error 10"}}'
    response.status_code = 200
    with pytest.raises(GeneralError):
        Fatsecret.valid_response(response)


@pytest.mark.integration
def test_valid_response_error_code_11():

    from fatsecret.fatsecret import Fatsecret, GeneralError

    response = requests.Response()
    response._content = b'{"error": {"code": 11, "message": "General error 11"}}'
    response.status_code = 200
    with pytest.raises(GeneralError):
        Fatsecret.valid_response(response)


@pytest.mark.integration
def test_valid_response_error_code_12():

    from fatsecret.fatsecret import Fatsecret, GeneralError

    response = requests.Response()
    response._content = b'{"error": {"code": 12, "message": "General error 12"}}'
    response.status_code = 200
    with pytest.raises(GeneralError):
        Fatsecret.valid_response(response)


@pytest.mark.integration
def test_valid_response_error_code_20():

    from fatsecret.fatsecret import Fatsecret, GeneralError

    response = requests.Response()
    response._content = b'{"error": {"code": 20, "message": "General error 20"}}'
    response.status_code = 200
    with pytest.raises(GeneralError):
        Fatsecret.valid_response(response)


@pytest.mark.integration
def test_valid_response_error_code_21():

    from fatsecret.fatsecret import Fatsecret, GeneralError

    response = requests.Response()
    response._content = b'{"error": {"code": 21, "message": "General error 21"}}'
    response.status_code = 200
    with pytest.raises(GeneralError):
        Fatsecret.valid_response(response)


@pytest.mark.integration
def test_valid_response_error_code_3_to_9(fatsecret_client):
    import requests

    from fatsecret.fatsecret import AuthenticationError, Fatsecret

    for code in range(3, 10):
        response = requests.Response()
        response._content = (
            f'{{"error": {{"code": {code}, "message": "Auth error {code}"}}}}'.encode()
        )
        response.status_code = 200
        with pytest.raises(AuthenticationError):
            Fatsecret.valid_response(response)


@pytest.mark.integration
def test_valid_response_error_code_101_to_108(fatsecret_client):
    import requests

    from fatsecret.fatsecret import Fatsecret, ParameterError

    for code in range(101, 109):
        response = requests.Response()
        response._content = (
            f'{{"error": {{"code": {code}, "message": "Param error {code}"}}}}'.encode()
        )
        response.status_code = 200
        with pytest.raises(ParameterError):
            Fatsecret.valid_response(response)


@pytest.mark.integration
def test_valid_response_error_code_201_to_207(fatsecret_client):
    import requests

    from fatsecret.fatsecret import ApplicationError, Fatsecret

    for code in range(201, 208):
        response = requests.Response()
        response._content = (
            f'{{"error": {{"code": {code}, "message": "App error {code}"}}}}'.encode()
        )
        response.status_code = 200
        with pytest.raises(ApplicationError):
            Fatsecret.valid_response(response)
