import datetime

from fatsecret import Fatsecret


def test_unix_time_epoch():
    assert Fatsecret.unix_time(datetime.datetime(1970, 1, 2)) == 1


def test_unix_time_v2_datetime():
    dt = datetime.datetime(1970, 1, 2)
    assert Fatsecret.unix_time_v2(dt) == 1


def test_unix_time_v2_date():
    dt = datetime.date(1970, 1, 3)
    assert Fatsecret.unix_time_v2(dt) == 2


def test_unix_time_v2_timestamp():
    ts = 86400 * 4  # 4 days after epoch
    assert Fatsecret.unix_time_v2(ts) == 4


def test_unix_time_v2_float_timestamp():
    ts = 86400.0 * 5  # 5 days after epoch
    assert Fatsecret.unix_time_v2(ts) == 5


def test_unix_time_v2_invalid_type():
    try:
        Fatsecret.unix_time_v2("not a date")
    except TypeError as e:
        assert "dt must be datetime, date, int, or float" in str(e)
    else:
        assert False, "TypeError not raised for invalid input type"


def test_unix_time_v2_leap_year():
    dt = datetime.datetime(1972, 1, 1)
    epoch = datetime.datetime(1970, 1, 1)
    expected_days = (dt - epoch).days
    assert Fatsecret.unix_time_v2(dt) == expected_days


def test_unix_time_v2_far_future():
    dt = datetime.datetime(2100, 1, 1)
    epoch = datetime.datetime(1970, 1, 1)
    expected_days = (dt - epoch).days
    assert Fatsecret.unix_time_v2(dt) == expected_days


def test_api_url_constant():
    fs = Fatsecret("key", "secret")
    assert fs.api_url == "https://platform.fatsecret.com/rest/server.api"
