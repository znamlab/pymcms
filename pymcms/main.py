"""Client helpers for the MCMS API."""

import re
import warnings

import requests
import yaml
from requests.exceptions import InvalidURL

BASE_URL = "https://crick.mcms-pro.com/api/"
SPECIAL_CHARACTERS = re.compile(r'[\',\.@"+=\-!#$%^&*<>?/\|}{~:]')


class MCMSError(Exception):
    """Raised when the MCMS API returns an application-level error."""


class McmsSession:
    """Authenticated session for the MCMS API."""

    def __init__(self, username, password, business_area=None, base_url=BASE_URL):
        self.username = username
        self.base_url = base_url
        self.session = None
        self.business_area = business_area
        self.log = []
        self.create_session(password)

    def create_session(self, password):
        """Create a session with authentication information."""
        if self.session is not None:
            print("Session already exists.")
            return

        session = requests.Session()
        session.headers.update(get_token(self.username, password))
        self.session = session
        self.log.append("Session created for user %s" % self.username)

    def _authenticated_session(self):
        """Return the active HTTP session, enforcing the session invariant."""
        if self.session is None:
            raise RuntimeError("No MCMS session has been created.")
        return self.session

    def get_animal(self, animal_id=None, name=None, barcode=None):
        """Get an animal from its name, ID, or barcode.

        If multiple values are provided, only the first non-``None`` value is used.

        Args:
            animal_id: Numerical ID of the animal.
            name: Name of the animal.
            barcode: Hexadecimal barcode of the animal.

        Returns:
            A dictionary with the animal information.
        """
        session = self._authenticated_session()
        if animal_id is not None:
            rep = session.get(f"{self.base_url}animals/{animal_id}")
        elif name is not None:
            rep = session.get(f"{self.base_url}animals/name/{name}")
        elif barcode is not None:
            rep = session.get(f"{self.base_url}animals/barcode/{barcode}")
        else:
            raise ValueError(
                'At least one of "animal_id", "name" or "barcode" must be provided'
            )

        if rep.ok and rep.status_code == 200:
            animal = rep.json()
            # Multiple arguments are allowed, so check that any non-primary value
            # matches the returned entity. The ID is always the primary lookup.
            if name is not None and animal["name"] != name:
                raise MCMSError(f"id `{animal_id}` does not match name `{name}`")
            if barcode is not None and animal["barcode"] != barcode:
                raise MCMSError(
                    f"id `{animal_id}` or name `{name}` do not match barcode "
                    f"`{barcode}`"
                )
            return animal
        return handle_error(rep)

    def get_procedures(self, animal_names=None, animal_id=None):
        """Get all procedures associated with animals.

        Given a list of animal names or a single animal ID, return all associated
        procedures.

        Args:
            animal_names: A list of animal names or a single animal name.
            animal_id: A single animal ID.

        Returns:
            A list of dictionaries with procedure information.
        """
        session = self._authenticated_session()
        if animal_id is not None and animal_names is not None:
            raise ValueError(
                "Only one of `animal_id` or `animal_names` can be provided"
            )
        if animal_id is not None:
            rep = session.get(f"{self.base_url}animalprocedures/animal/{animal_id}")
        elif animal_names is not None:
            if isinstance(animal_names, str):
                animal_names = [animal_names]
            else:
                animal_names = [str(name) for name in animal_names]
            rep = session.post(
                f"{self.base_url}animalprocedures",
                data=",".join(animal_names).encode(),
                headers={"Content-Type": "text/plain"},
            )
        else:
            raise ValueError(
                'At least one of "animal_id" or "animal_names" must be provided'
            )
        if rep.ok and rep.status_code == 200:
            return rep.json()
        return handle_error(rep)


def handle_error(rep):
    """Handle an API response whose status code is not 200."""
    if rep.ok:
        warnings.warn(
            f"The API returned unexpected status code {rep.status_code}.",
            stacklevel=2,
        )
        return rep
    if rep.status_code == 400:
        raise MCMSError(
            f"Error {rep.status_code}. This entity does not exist:"
            f"{rep.url.split('/')[-1]}"
        )
    if rep.status_code == 404:
        raise InvalidURL(rep.content)

    raise OSError(f"Unknown error with status code {rep.status_code}")


def parse_error(error_message):
    """Parse the YAML message returned by an MCMS bad request."""
    if isinstance(error_message, bytes):
        error_message = error_message.decode("utf8")
    return yaml.safe_load(error_message)


def get_token(username, password, base_url=BASE_URL):
    """Log in and return the authorization headers for an MCMS session."""
    try:
        rep = requests.post(
            f"{base_url}authenticate",
            headers={"Accept": "*/*", "username": username, "password": password},
        )
    except requests.exceptions.ConnectionError as error:
        raise requests.exceptions.ConnectionError(
            "Cannot connect to MCMS. Are you on the institution network?"
        ) from error
    if not rep.ok:
        raise OSError(f"Failed to authenticate. Got an error {rep.status_code}")
    return {"Authorization": f"Bearer {rep.json()['token']}"}
