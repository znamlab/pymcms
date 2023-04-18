import pytest
from requests.exceptions import InvalidURL
from pymcms import main

TEST_ANIMAL = {
    "id": 1848463,
    "name": "BRAC7449.2a",
    "birthDate": "18-Aug-2022",
    "barcode": "M01848463",
}
TEST_ANIMAL_LIST = ["PZAA16.1a", "PZAA16.1b", "PZAA16.1c"]
USER = "ab8"
try:
    from flexiznam import get_password

    PASSWORD = get_password(USER, "mcms")
except ImportError:
    PASSWORD = None
    if PASSWORD is None:
        print("Cannot run tests without flexiznam installed and no password provided")


def test_get_token():
    token = main.get_token(username=USER, password=PASSWORD)
    assert token is not None


def test_create_session():
    mcms_sess = main.McmsSession(username=USER, password=PASSWORD)
    assert mcms_sess is not None
    assert "Authorization" in mcms_sess.session.headers


def test_get_animal():
    mcms_sess = main.McmsSession(username=USER, password=PASSWORD)
    byid = mcms_sess.get_animal(animal_id=TEST_ANIMAL["id"])
    assert byid["name"] == TEST_ANIMAL["name"]
    assert byid["birthDate"] == TEST_ANIMAL["birthDate"]
    assert byid["barcode"] == TEST_ANIMAL["barcode"]
    byname = mcms_sess.get_animal(name=TEST_ANIMAL["name"])
    assert byname == byid
    bybarcode = mcms_sess.get_animal(barcode=TEST_ANIMAL["barcode"])
    assert bybarcode == byid

    # test error handling
    with pytest.raises(main.MCMSError):
        mcms_sess.get_animal(animal_id=TEST_ANIMAL["id"], name="wrong name")
    with pytest.raises(InvalidURL):
        mcms_sess.get_animal(name="wrongid")
    with pytest.raises(InvalidURL):
        mcms_sess.get_animal(animal_id="wrongid")
    with pytest.raises(InvalidURL):
        mcms_sess.get_animal(animal_id="wrongbarcode")


def test_get_procedures():
    mcms_sess = main.McmsSession(username=USER, password=PASSWORD)
    proc = mcms_sess.get_procedures(animal_names=TEST_ANIMAL["name"])
    assert proc is not None
    assert len(proc) > 0
    assert all([p["animal"]["name"] == TEST_ANIMAL["name"] for p in proc])
    multi_proc = mcms_sess.get_procedures(animal_names=TEST_ANIMAL_LIST)
    assert len(proc) > 0
    animal_names = [p["animal"]["name"] for p in multi_proc]
    assert all([animal in TEST_ANIMAL_LIST for animal in animal_names])
    assert all([animal in animal_names for animal in TEST_ANIMAL_LIST])
    rep = mcms_sess.get_procedures(animal_names="wrongname")
    assert not rep
