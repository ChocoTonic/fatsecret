import datetime

from fatsecret import Fatsecret


def test_unix_time_epoch():
    assert Fatsecret.unix_time(datetime.datetime(1970, 1, 2)) == 1


def test_api_url_constant():
    fs = Fatsecret("key", "secret")
    assert fs.api_url == "https://platform.fatsecret.com/rest/server.api"
