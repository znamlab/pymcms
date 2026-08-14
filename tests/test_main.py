from unittest.mock import Mock, patch

import pytest
from requests.exceptions import ConnectionError, InvalidURL

from pymcms import main

TEST_ANIMAL = {
    "id": 1848463,
    "name": "BRAC7449.2a",
    "birthDate": "2022-08-18T23:00:00.000+0000",
    "barcode": "M01848463",
}


def response(*, status_code=200, body=None, content=b"", url="https://mcms.test/api"):
    """Build a minimal stand-in for a ``requests.Response``."""
    return Mock(
        ok=200 <= status_code < 400,
        status_code=status_code,
        json=Mock(return_value=body),
        content=content,
        url=url,
    )


def session():
    """Create an authenticated session without making a network request."""
    with patch.object(
        main, "get_token", return_value={"Authorization": "Bearer test-token"}
    ):
        return main.McmsSession("test-user", "test-password")


def test_get_token_returns_authorization_header():
    api_response = response(body={"token": "test-token"})

    with patch.object(main.requests, "post", return_value=api_response) as post:
        assert main.get_token("test-user", "test-password") == {
            "Authorization": "Bearer test-token"
        }

    post.assert_called_once_with(
        "https://crick.mcms-pro.com/api/authenticate",
        headers={"Accept": "*/*", "username": "test-user", "password": "test-password"},
    )


def test_get_token_reports_connection_errors():
    with patch.object(main.requests, "post", side_effect=ConnectionError):
        with pytest.raises(ConnectionError, match="institution network"):
            main.get_token("test-user", "test-password")


def test_create_session_adds_authorization_header():
    mcms_session = session()

    assert mcms_session.session.headers["Authorization"] == "Bearer test-token"
    assert mcms_session.log == ["Session created for user test-user"]


def test_get_animal_uses_each_supported_lookup():
    mcms_session = session()
    mcms_session.session = Mock()
    mcms_session.session.get.return_value = response(body=TEST_ANIMAL)

    assert mcms_session.get_animal(animal_id=TEST_ANIMAL["id"]) == TEST_ANIMAL
    mcms_session.session.get.assert_called_with(
        "https://crick.mcms-pro.com/api/animals/1848463"
    )

    assert mcms_session.get_animal(name=TEST_ANIMAL["name"]) == TEST_ANIMAL
    mcms_session.session.get.assert_called_with(
        "https://crick.mcms-pro.com/api/animals/name/BRAC7449.2a"
    )

    assert mcms_session.get_animal(barcode=TEST_ANIMAL["barcode"]) == TEST_ANIMAL
    mcms_session.session.get.assert_called_with(
        "https://crick.mcms-pro.com/api/animals/barcode/M01848463"
    )


def test_get_animal_validates_lookup_arguments():
    mcms_session = session()
    mcms_session.session = Mock()
    mcms_session.session.get.return_value = response(body=TEST_ANIMAL)

    with pytest.raises(main.MCMSError, match="does not match name"):
        mcms_session.get_animal(animal_id=TEST_ANIMAL["id"], name="wrong name")

    with pytest.raises(ValueError, match="At least one"):
        mcms_session.get_animal()


def test_get_procedures_uses_supported_requests():
    mcms_session = session()
    mcms_session.session = Mock()
    mcms_session.session.get.return_value = response(body=[{"id": 1}])
    mcms_session.session.post.return_value = response(body=[{"id": 2}])

    assert mcms_session.get_procedures(animal_id=TEST_ANIMAL["id"]) == [{"id": 1}]
    mcms_session.session.get.assert_called_once_with(
        "https://crick.mcms-pro.com/api/animalprocedures/animal/1848463"
    )

    assert mcms_session.get_procedures(animal_names=["first", "second"]) == [{"id": 2}]
    mcms_session.session.post.assert_called_once_with(
        "https://crick.mcms-pro.com/api/animalprocedures",
        data=b"first,second",
        headers={"Content-Type": "text/plain"},
    )


def test_get_procedures_requires_exactly_one_lookup_method():
    mcms_session = session()

    with pytest.raises(ValueError, match="Only one"):
        mcms_session.get_procedures(animal_id=1, animal_names=["test"])

    with pytest.raises(ValueError, match="At least one"):
        mcms_session.get_procedures()


def test_handle_error_maps_known_status_codes():
    with pytest.raises(main.MCMSError, match="does not exist"):
        main.handle_error(
            response(status_code=400, url="https://mcms.test/animals/unknown")
        )

    with pytest.raises(InvalidURL):
        main.handle_error(response(status_code=404, content=b"not found"))


def test_parse_error_accepts_bytes_and_text():
    message = (
        "type: validation\nmessage: Invalid value\ndescription: Name is required\n"
    )
    expected = {
        "type": "validation",
        "message": "Invalid value",
        "description": "Name is required",
    }

    assert main.parse_error(message) == expected
    assert main.parse_error(message.encode()) == expected
