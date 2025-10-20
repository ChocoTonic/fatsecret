from unittest.mock import MagicMock, patch

from fatsecret.auth import fatsecret_authenticate


@patch("fatsecret.auth.requests.Session")
@patch("fatsecret.auth.Fatsecret")
@patch("fatsecret.auth.BeautifulSoup")
def test_fatsecret_authenticate_success(mock_bs, mock_fatsecret, mock_session):
    # Setup mocks
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_fatsecret_instance = MagicMock()
    mock_fatsecret.return_value = mock_fatsecret_instance
    mock_fatsecret_instance.get_authorize_url.return_value = (
        "https://example.com/authorize"
    )

    # Mock BeautifulSoup for login page
    mock_login_soup = MagicMock()
    mock_login_soup.find.side_effect = [
        {"value": "viewstate_value"},
        {"value": "viewstate_generator_value"},
    ]
    # Mock BeautifulSoup for pin page
    mock_pin_soup = MagicMock()
    mock_pin_tag = MagicMock()
    mock_pin_tag.text = "123456"
    mock_pin_soup.find.return_value = mock_pin_tag
    mock_bs.side_effect = [mock_login_soup, mock_pin_soup]

    # Mock responses
    mock_login_response = MagicMock()
    mock_login_response.text = "login_html"
    mock_session_instance.get.return_value = mock_login_response
    mock_pin_response = MagicMock()
    mock_pin_response.content = b"pin_html"
    mock_session_instance.post.return_value = mock_pin_response

    # Run
    result = fatsecret_authenticate("user", "pass", "ckey", "csecret")

    # Assert
    assert result == mock_fatsecret_instance
    mock_fatsecret_instance.authenticate.assert_called_once_with("123456")


@patch("fatsecret.auth.requests.Session")
@patch("fatsecret.auth.Fatsecret")
@patch("fatsecret.auth.BeautifulSoup")
def test_fatsecret_authenticate_fail_pin(mock_bs, mock_fatsecret, mock_session):
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_fatsecret_instance = MagicMock()
    mock_fatsecret.return_value = mock_fatsecret_instance
    mock_fatsecret_instance.get_authorize_url.return_value = (
        "https://example.com/authorize"
    )
    mock_login_soup = MagicMock()
    mock_login_soup.find.side_effect = [
        {"value": "viewstate_value"},
        {"value": "viewstate_generator_value"},
    ]
    mock_pin_soup = MagicMock()
    mock_pin_soup.find.return_value = None  # No PIN found
    mock_bs.side_effect = [mock_login_soup, mock_pin_soup]
    mock_login_response = MagicMock()
    mock_login_response.text = "login_html"
    mock_session_instance.get.return_value = mock_login_response
    mock_pin_response = MagicMock()
    mock_pin_response.content = b"pin_html"
    mock_session_instance.post.return_value = mock_pin_response
    result = fatsecret_authenticate("user", "pass", "ckey", "csecret")
    assert result is None
