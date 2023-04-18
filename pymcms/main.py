"""Generic function to interface with flexilims"""
import math
import re
import requests
from requests.exceptions import InvalidURL
import warnings
from requests.auth import HTTPBasicAuth
import json

BASE_URL = "https://crick-uat.colonymanagement.org/api/"
SPECIAL_CHARACTERS = re.compile(r'[\',\.@"+=\-!#$%^&*<>?/\|}{~:]')


class MCMSError(Exception):
    """Error in MCMS code"""

    pass


class McmsSession(object):
    def __init__(self, username, password, business_area=None, base_url=BASE_URL):
        self.username = username
        self.base_url = base_url
        self.session = None
        self.business_area = business_area
        self.log = []
        self.create_session(password)

    def create_session(self, password):
        """Create a session with authentication information"""
        if self.session is not None:
            print("Session already exists.")
            return

        session = requests.Session()
        tok = get_token(self.username, password)

        session.headers.update(tok)
        self.session = session
        self.log.append("Session created for user %s" % self.username)

    def get_animal(self, animal_id=None, name=None, barcode=None):
        """Get a animal from its name, id or barcode

        If multiple values are provied, only the first non None value will be used.

        Args:
            animal_id:  numerical id of the animal
            name: name of the animal
            barcode: hexadecimal barcode of the animal

        Returns:
            a dictionary with the animal information
        """

        if animal_id is not None:
            rep = self.session.get(f"{self.base_url}animals/{animal_id}")
        elif name is not None:
            rep = self.session.get(f"{self.base_url}animals/name/{name}")
        elif barcode is not None:
            rep = self.session.get(f"{self.base_url}animals/barcode/{barcode}")
        else:
            raise ValueError(
                'At least one of "animal_id", "name" or "barcode" must be provided'
            )

        if rep.ok and (rep.status_code == 200):
            json = rep.json()
            # since one can provide multiple arguments, we need to check that they do
            # match the returned value
            # no need to check ID since it's the first to be used
            if (name is not None) and (json["name"] != name):
                raise MCMSError(f"id {animal_id} does not match name {name}")
            if (barcode is not None) and (json["barcode"] != barcode):
                raise MCMSError(
                    f"id {animal_id} or name {name} do not match barcode {barcode}"
                )

            return json
        handle_error(rep)

    def get_procedures(self, animal_names):
        """Get all procedures associates with a list of animals

        Args:
            animal_names: a list of animal names or a single animal name

        Returns:
            a list of dictonaries with procedure information"""

        if isinstance(animal_names, str):
            animal_names = [animal_names]
        else:
            animal_names = [str(x) for x in animal_names]
        animal_names = ",".join(animal_names)
        rep = self.session.post(
            f"{self.base_url}procedures",
            data=animal_names.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
        )
        if rep.ok and (rep.status_code == 200):
            return rep.json()
        handle_error(rep)


def handle_error(rep):
    """handles responses that have a status code != 200"""
    # error handling:
    if rep.ok:
        warnings.warn(
            "Warning. Seems ok but I had an unknown status code %s" % rep.status_code
        )
        warnings.warn("Will return the response object without interpreting it.")
        warnings.warn("see response.json() to (hopefully) get the data.")
        return rep
    if rep.status_code == 400:
        raise MCMSError(
            f"Error {rep.status_code}. This entity does not exists:"
            + f"{rep.url.split('/')[-1]}"
        )
    if rep.status_code == 404:
        raise InvalidURL(f"Page not found, maybe this entity doesn't exist: {rep.url}")

    raise IOError("Unknown error with status code %d" % rep.status_code)


def parse_error(error_message):
    """Parse the error message from MCMS bad request

    The messages are html pages with a bold "Type", "Message" and "Description" fields
    """
    if isinstance(error_message, bytes):
        error_message = error_message.decode("utf8")
    regexp = (
        ".*<b>Type</b>(.*)</p><p><b>Message</b>(.*)</p><p><b>Description</b>(.*)</p>"
    )
    m = re.match(pattern=regexp, string=error_message)
    return {name: v for name, v in zip(("type", "message", "description"), m.groups())}


def get_token(username, password, base_url=BASE_URL):
    """Login to the database and create headers with the proper token"""
    try:
        rep = requests.post(
            base_url + "authenticate",
            headers=dict(Accept="*/*", username=username, password=password),
        )
    except requests.exceptions.ConnectionError:
        raise requests.exceptions.ConnectionError(
            "Cannot connect to mcms. " "Are you on the insitution network?"
        )
    if rep.ok:
        token = rep.json()["token"]
    else:
        raise IOError("Failed to authenticate. Got an error %d" % rep.status_code)

    headers = {"Authorization": "Bearer %s" % token}
    return headers
