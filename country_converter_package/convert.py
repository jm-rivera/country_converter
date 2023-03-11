import warnings
from typing import Collection, Iterable, List, Sequence, Union
import re

from country_converter_package.classification_data import ClassificationData
from country_converter_package.correspondence import ClassificationCorrespondence

DATA: ClassificationData = ClassificationData()


def _check_pandas():
    try:
        import pandas as optional_pd

        return optional_pd
    except ImportError:
        return None


class CountryConverter:
    """The CountryConverter class is used to convert input names from one
    classification system to another.

    The class takes a matcher argument, which is an
    instance of the ClassificationCorrespondence class.
    If no matcher argument is provided, the class initializes a new
    ClassificationCorrespondence instance using DATA and "iso3" as the
    classification data and the target classification, respectively.

    The convert method of the class performs the actual conversion of names.
    """

    matcher: ClassificationCorrespondence

    def __init__(self, matcher: Union[ClassificationCorrespondence, None] = None):
        if matcher is None:
            matcher = ClassificationCorrespondence(DATA, "iso3")

        self.matcher = matcher

    @staticmethod
    def _validate_names_type(
        names: Union[List, Collection, Sequence, str, int]
    ) -> Union[List, Iterable]:
        """Validate the input names type.

        Args:
            names: The input names to convert.

        Returns:
            The input names as an Iterable.

        """

        # If the input is a string, int or float, convert it to a list.
        if isinstance(names, (str, int, float)):
            names = [names]

        # If the input is not a list-like object, raise a TypeError.
        if not isinstance(names, Iterable):
            raise TypeError(
                "names must be a list-like object, a string, an int or a float"
            )

        return names

    @staticmethod
    def _validate_additional_mapping(additional_mapping: Union[None, dict]) -> dict:
        """Validate the additional_mapping argument.

        Validating also means transforming all keys to lowercase.

        Args:
            additional_mapping: A dictionary of additional mappings to use.

        Returns:
            The additional_mapping argument as a dictionary, or an empty dictionary if
            additional_mapping is None.

        """

        # If additional_mapping is None, return an empty dictionary.
        if additional_mapping is None:
            return {}
        # Else, transform all keys to lowercase and return the dictionary.
        else:
            new_mapping = {}
            for k, v in additional_mapping.items():
                if isinstance(k, str):
                    new_mapping[k.lower()] = v
            return new_mapping

    @staticmethod
    def _separate_exclude_cases(name, exclude_prefix):
        """Splits the excluded

        Parameters
        ----------
        name : str
            Name of the country/region to convert.

        exclude_prefix : list of valid regex strings
            List of indicators, which negate the subsequent country/region.
            These prefixes and everything following will not be converted.
            E.g. 'Asia excluding China' becomes 'Asia' and
            'China excluding Hong Kong' becomes 'China' before conversion


        Returns
        -------

        dict with
            'clean_name' : str
                as name without anything following exclude_prefix
            'excluded_countries' : list
                list of excluded countries.

        """

        excluder = re.compile("|".join(exclude_prefix))
        split_entries = excluder.split(name)
        return {"clean_name": split_entries[0], "excluded_countries": split_entries[1:]}

    def _validate_class(self, classification: Union[str, None]) -> Union[str, None]:
        """Validate the source classification by finding the closest match in the
        classification data.

        Args:
            classification (str): The name of the classification.

        """
        import difflib

        # If classification is None, return None.
        if classification is None:
            return None
        # If the classification is 'regex' then return 'regex'.
        elif classification.lower() == "regex":
            return "regex"
        # Otherwise, find the closest match in valid classifications.
        else:
            # find the closest match
            matches = difflib.get_close_matches(
                classification.lower(),
                self.matcher.classification_data.get_valid_classifications(),
                cutoff=0.55,
            )
        # return the lowercase first match or None if there are no matches.
        return str(matches[0]).lower() if len(matches) > 0 else None

    def convert(
        self,
        names: Union[List, Collection, Sequence, str, int],
        from_class: Union[None, str] = None,
        to: str = "iso3",
        enforce_list: bool = False,
        not_found: Union[str, None] = None,
        exclude_prefix: Union[None, list] = None,
        additional_mapping: Union[None, dict] = None,
        src: Union[None, str] = None,  # backward compatibility
    ) -> list:
        """Converts input names from one geographic classification system to another.

        Args:
            names: The names to be converted.
            from_class: The source classification system. Defaults to None.
            to: The target classification system. Defaults to "iso3".
            enforce_list: Whether to return a list even when the input is a single name.
                Defaults to False.
            not_found: The value to use for names that cannot be mapped.
                Defaults to None.
            exclude_prefix: A list of prefixes to exclude when searching for
                correspondences. Defaults to None.
            additional_mapping: A dictionary of additional correspondences to add.
                Defaults to None.
            src: The source classification system for backward compatibility.
                Defaults to None. Raises future warning when used.

        Returns:
            The converted names.

        Raises:
            KeyError: When both `src` and `from_class` are provided and they are different.

        """
        # Check for deprecated src
        if src is not None:
            warnings.warn(
                "Using 'src' will be deprecated in a future version. "
                "Please switch to using `from_class` instead",
                FutureWarning,
            )
            from_class = src

        # Check for src and from_class
        if (src is not None and from_class is not None) and (src != from_class):
            raise KeyError("Only one of 'src' or 'from_class' can be used")

        # Set default exclude_prefix
        if exclude_prefix is None:
            exclude_prefix = ["excl\\w.*", "without", "w/o"]

        # validate the source and to classifications
        from_class = self._validate_class(from_class)
        to = self._validate_class(to)

        # Validate input
        names = self._validate_names_type(names)
        additional_mapping = self._validate_additional_mapping(additional_mapping)

        # Create correspondence dictionary
        correspondence: dict = (
            self.matcher.correspondence_dictionary(
                keys=names,
                source=from_class,
                target=to,
                default=not_found,
                exclude_prefix=exclude_prefix,
            )
            | additional_mapping
        )

        # check pandas dependency
        optional_pd = _check_pandas()

        # If pandas is installed, use pandas.Series.map if the input is a pandas.Series.
        if optional_pd is not None and isinstance(names, optional_pd.Series):
            converted_names = names.map(correspondence)
        # If pandas is not installed, use map and return a list.
        else:
            converted_names = list(map(correspondence.get, names))

        # If enforce_list is False and there is only one name, return the name.
        if not enforce_list and len(converted_names) == 1:
            return converted_names[0]

        return converted_names


if __name__ == "__main__":
    cc = CountryConverter()

    result = cc.convert("GTM", src="iso3", to="ISO2")
