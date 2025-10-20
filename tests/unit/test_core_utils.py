import datetime

from fatsecret import Fatsecret


def test_unix_time_epoch():
    dt = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
    dt_naive = dt.replace(tzinfo=None)
    assert Fatsecret.unix_time(dt_naive) == 0


def test_unix_time_one_day():
    dt = datetime.datetime.fromtimestamp(0, datetime.timezone.utc) + datetime.timedelta(
        days=1
    )
    dt_naive = dt.replace(tzinfo=None)
    assert Fatsecret.unix_time(dt_naive) == 1


def test_unix_time_leap_year():
    dt = datetime.datetime(1972, 1, 1, tzinfo=datetime.timezone.utc)
    epoch = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
    dt_naive = dt.replace(tzinfo=None)
    epoch_naive = epoch.replace(tzinfo=None)
    expected_days = (dt_naive - epoch_naive).days
    assert Fatsecret.unix_time(dt_naive) == expected_days


def test_unix_time_far_future():
    dt = datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)
    epoch = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
    dt_naive = dt.replace(tzinfo=None)
    epoch_naive = epoch.replace(tzinfo=None)
    expected_days = (dt_naive - epoch_naive).days
    assert Fatsecret.unix_time(dt_naive) == expected_days


def test_api_url_constant():
    fs = Fatsecret("key", "secret")
    assert fs.api_url == "https://platform.fatsecret.com/rest/server.api"
