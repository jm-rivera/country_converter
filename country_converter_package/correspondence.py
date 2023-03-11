import logging
import re

from typing import Collection, Sequence, Union

from country_converter_package.classification_data import ClassificationData

log = logging.getLogger(__name__)


class ClassificationCorrespondence:
    """A class for retrieving correspondence data between different classifications.

    Attributes:
        classification_data (ClassificationData): An object representing the classification data.
        target (str): The name of the target classification.
    Methods:
        guess_format: A class method that guesses
        the format of a given name (either "ISOnumeric", "ISO2", "ISO3", or "regex").
        match_key: Returns the value in the target classification for the given key.
        correspondence_dictionary: Returns a dictionary with the keys as keys,
         and the values in the target classification as values.

    """

    classification_data: ClassificationData
    target: str

    def __init__(self, classification_data: ClassificationData, target: str):
        self.classification_data = classification_data
        self.target = target

    def __repr__(self):
        return f"{self.__class__.__name__}(to: {self.target})"

    def __str__(self):
        return self.__repr__()

    @classmethod
    def guess_format(cls, name: Union[str, int]) -> str:
        try:
            int(name)
            src_format = "isonumeric"
        except ValueError:
            if len(name) == 2:
                src_format = "iso2"
            elif len(name) == 3:
                src_format = "iso3"
            else:
                src_format = "regex"
        return src_format

    def match_key(self, key: str, target: str, default=None):
        """
        Return the value in the target classification for the given key.

        Args:
            key (str): The key to search for in the classification data. If the classification
                data source is 'regex', the key is treated as a regular expression pattern.
            target (str): The name of the classification to retrieve the value from.
            default: The value to return if the key is not found in the classification data.

        Returns:
            str: The value of the key in the specified classification, or the default value
                if the key is not found.

        Raises:
            Warning: If the key is not found in the classification data or there are multiple
                matches when the classification data source is 'regex'.
        """

        # If the key is a regex, we need to find the matching key.
        if self.classification_data.source_classification in ["regex", "iso2"]:
            # Find all keys that match the key
            matching = [
                k for k in self.classification_data.data.keys() if k.search(key.lower())
            ]

            # Warn if there are multiple matches
            if len(matching) > 1:
                log.warning(f"More than 1 match for {key}: {matching}")
            # If there are no matches, return None
            if len(matching) < 1:
                log.warning(
                    f"{key} not found in"
                    f" {self.classification_data.source_classification}"
                )
                return default
            # Keep the first match
            key = matching[0]

        # If the key is not in the data, return None
        if isinstance(key, str):
            key_lower = key.lower()
        else:
            key_lower = key
        if key_lower not in self.classification_data.data:
            log.warning(
                f"'{key}' not found in "
                f"{self.classification_data.source_classification}"
            )
            return default

        # Match the key to the value in the target classification
        if target == "iso2":
            clean_result = self.classification_data.data[key_lower][target]
            return re.sub("[^a-zA-Z]+", "", clean_result.split("|")[0])

        return self.classification_data.data[key_lower][target]

    @staticmethod
    def _separate_exclude_cases(name, exclude_prefix):
        """Splits the excluded

        Parameters
        ----------
        name : str
            Name of the country/region to convert.

        exclude_prefix : list of valid regex strings
            List of indicators which negate the subsequent country/region.
            These prefixes and everything following will not be converted.
            E.g. 'Asia excluding China' becomes 'Asia' and
            'China excluding Hong Kong' becomes 'China' prior to conversion


        Returns
        -------

        dict with
            'clean_name' : str
                as name without anything following exclude_prefix
            'excluded_countries' : list
                list of excluded countries

        """

        exclude_regex = re.compile("|".join(exclude_prefix))
        split_entries = exclude_regex.split(name)
        return {
            "clean_name": split_entries[0].strip(),
            "excluded_countries": [c.strip() for c in split_entries[1:]],
        }

    def correspondence_dictionary(
        self,
        keys: Union[Collection, Sequence, str, int],
        *,
        source: Union[None, str] = None,
        target: str,
        default: Union[str, None] = None,
        exclude_prefix: list = None,
    ):
        """Return a dictionary with the keys as keys, and the values in the target
        classification as values

        Parameters
        ----------
        keys : A list-like, Collection, str or int. The data to be matched.
        source : A valid source classification. If None, the source will be guessed.
        target : A valid target classification.
        default : The default value to be returned if the key is not found. If None,
              the key will be returned.
        exclude_prefix : A list of prefixes to exclude from the keys.


        Returns
        -------

        A dictionary with the keys as keys, and the values in the target

        """

        # If the keys are a string or int, convert to a list.
        if isinstance(keys, (str, int)):
            keys = [keys]

        # If the keys are a list, convert to a set to remove duplicates.
        unique_keys = set(keys)

        # Create a dictionary to store the matches
        match = {}

        # For each key, find the match in the target classification
        for _ in unique_keys:

            # If the source is not specified, guess the source
            if source is None:
                source = self.guess_format(_)

            # If the source is different from the current source, set the source
            if source != self.classification_data.source_classification:
                self.classification_data.set_source(source)

            if exclude_prefix is not None:
                _ = self._separate_exclude_cases(_, exclude_prefix)["clean_name"]

            # Find the match
            d_ = _ if default is None else default
            match[_] = self.match_key(key=_, target=target, default=d_)

        return match
