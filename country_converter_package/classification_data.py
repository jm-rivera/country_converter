import logging
import re
from dataclasses import dataclass, field
from typing import Optional, Union
import json

from country_converter_package import _check_pandas, FILE

log = logging.getLogger(__name__)

UNIQUE = ["name_short", "name_official", "regex"]
STRING = UNIQUE + [
    "ISO2",
    "ISO3",
    "continent",
    "UNregion",
    "EXIO1",
    "EXIO2",
    "EXIO3",
    "WIOD",
]


optional_pd = _check_pandas()


def _check_unique_names_df(df):
    """Checks if the names in the input dataframe are unique."""
    for name_entry in UNIQUE:
        if df[name_entry].duplicated().any():
            log.warning(f"Duplicated values in column {name_entry}")


def _pandas_loader(data: Union[optional_pd.DataFrame, str]):
    """Loads the classification data from a CSV file using pandas."""

    if isinstance(data, optional_pd.DataFrame):
        _check_unique_names_df(data)
        return data

    else:
        loaded_data = optional_pd.read_csv(
            data,
            sep="\t",
            encoding="utf-8",
            converters={str_col: str for str_col in STRING},
        )
        _check_unique_names_df(loaded_data)
        return loaded_data


def _df_to_dict(df: optional_pd.DataFrame, index: str) -> dict:
    """Converts a dataframe to a dictionary."""
    columns = [c for c in df.columns if c != index]

    return df.set_index(index)[columns].to_dict("index")


def _read_additional_data(
    data: Union[optional_pd.DataFrame, str, list]
) -> optional_pd.DataFrame:
    """Reads additional data from provided file(s)"""
    if optional_pd.DataFrame is None:
        raise ImportError(
            "Pandas is required to load the classification data from a CSV file."
        )

    if isinstance(data, str):
        data = [data]

    files = []

    for file in data:
        files.append(_pandas_loader(file))

    # Concatenate all the dataframes into a single dataframe.
    files = optional_pd.concat(files, ignore_index=True)

    # Convert the dataframe to a dictionary.
    files = _df_to_dict(files, "regex")

    return files


def _check_int(value: Union[int, str, float]) -> Union[int, str, float]:
    """Converts the input to an integer if possible.

    If the input can be converted to an integer, the function returns the integer value.
    If the input cannot be converted to an integer, the function returns the input value.

    Args:
        value: The value to be checked and possibly converted to an integer.

    Returns:
        If the input can be converted to an integer, returns the integer value.
             Otherwise, it returns the input value.

    Example:
        >>> _check_int(5)
        5
        >>> _check_int("5")
        5
        >>> _check_int("5.5")
        "5.5"
    """

    try:
        # Try to convert the input to an integer.
        return int(value)
    # If the input cannot be converted to an integer, return the input value.
    except ValueError:
        return value


def _convert_int(data: dict) -> dict:
    """
    Converts the string keys and values of a nested dictionary to integers, if possible.

    This function recursively checks all the keys and values in the input dictionary to see
    if they can be converted to integers. If a key or value can be converted to an integer,
    it is replaced with the integer value. Otherwise, the key or value is left unchanged.

    Args:
        data (dict): The nested dictionary to be converted.

    Returns:
        dict: The converted dictionary.

    Raises:
        None.

    Example:
        >>> sample = {'a': {'1': '100', '2': {'3': '200'}}, 'b': '300'}
        >>> _convert_int(sample)
        {'a': {1: 100, 2: {3: 200}}, 'b': 300}
    """

    # Iterate through all the key-value pairs in the input dictionary.
    for k, v in data.items():
        # If the value is a dictionary, recursively call this function.
        if isinstance(v, dict):
            _convert_int(v)
        else:
            # If the key is a string, check if it can be converted to an integer.
            if isinstance(k, str):
                data[k] = _check_int(v)
                k = _check_int(k)

            # If the value is a string, check if it can be converted to an integer.
            data[k] = _check_int(v)

    return data


def _to_lower(data: dict) -> dict:
    """
    Converts the string keys and values of a nested dictionary to lower case, if possible.

    This function recursively checks all the keys and values in the input dictionary to see
    if they can be to lowercase strings.

    Args:
        data (dict): The nested dictionary to be converted.

    Returns:
        dict: The converted dictionary.

    Raises:
        None.
    """
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if isinstance(k, str):
                k = k.lower()
            new_dict[k] = _to_lower(v)
        return new_dict
    else:
        return data


def _keys_to_int(data: dict) -> dict:
    """Converts the string keys of a dictionary to integers.

    This function iterates through all the key-value pairs in the input dictionary,
    and converts the string keys to integers using the _check_int() function. The
    original keys are replaced with the integer keys in the output dictionary.

    Args:
        data (dict): The dictionary to be converted.

    Returns:
        dict: The converted dictionary.

    Raises:
        None.

    Example:
        >>> sample_data = {'1': 'one', '2': 'two', '3': 'three'}
        >>> _keys_to_int(sample_data)
        {1: 'one', 2: 'two', 3: 'three'}
    """
    # Create a new dictionary to store the converted data.
    new_dict = {}

    # Iterate through all the key-value pairs in the input dictionary.
    for k, v in data.items():
        # Keep the original value for completeness
        new_dict[k] = v
        # Convert the key to an integer, if possible.
        k = _check_int(k)
        # Add the key-value pair to the new dictionary.
        new_dict[k] = v

    return new_dict


def _compile_regex_keys(data: dict) -> dict:
    """Compiles regular expression patterns for the keys of a dictionary.

    This function takes a dictionary as input, and compiles a regular expression pattern
    for each key using the re.compile() function. The original keys are replaced with the
    compiled regex patterns in the output dictionary.

    Args:
        data (dict): The dictionary whose keys will be compiled as regular expression patterns.

    Returns:
        dict: The new dictionary with compiled regex patterns as keys.

    Raises:
        None.

    Example:
        >>> sample = {'foo': 1, 'bar': 2, 'baz': 3}
        >>> _compile_regex_keys(sample)
        {re.compile('foo'): 1, re.compile('bar'): 2, re.compile('baz'): 3}"""

    return {re.compile(k): v for k, v in data.items()}


def _get_unique_keys(dictionary: dict) -> set:
    """
    Returns a set of unique keys in a dictionary.

    Args:
        dictionary (dict): The dictionary whose keys will be returned.

    Returns:
        set: A set of unique keys in the dictionary.
    """
    keys = []
    for k, v in dictionary.items():
        if isinstance(v, dict):
            keys.append(_get_unique_keys(v))
        else:
            keys.append(k)
    try:
        return set(keys)
    except TypeError:
        return set().union(*keys)


def _change_top_key_value(new_key: str, d: dict, to_lower: bool = True) -> dict:

    """Creates a new dictionary with the top-level key changed to a new value.

    This function takes a dictionary as input, and creates a new dictionary with the top-level
    key changed the key of one of the nested dictionaries, as specified by the user.
    The function raises a ValueError if the new key is not found in any nested dictionary.

    Args:
        new_key (str): The new key to be used as the top-level key in the output dictionary.
        d (dict): The dictionary whose top-level key is to be changed.

    Returns:
        dict: The new dictionary with the top-level key changed to the new value.

    Raises:
        KeyError: If the new key is not found in the dictionary.

    """
    # convert to lower
    if to_lower:
        d = _to_lower(d)

    # Create a new dictionary to store the converted data.
    new_dict = {}

    # categories
    unique_keys = _get_unique_keys(d)

    # Check if the new key is in the dictionary.
    if new_key not in unique_keys:
        raise KeyError(f"Key {new_key} not found in dictionary")

    # Iterate through all the key-value pairs in the input dictionary.
    for k, v in d.items():
        # Get the new key value.
        nk = d[k][new_key]
        # Skip the key-value pair if the new key value is empty.
        if nk == "":
            continue
        # Add the key-value pair to the new dictionary.
        new_dict[nk] = {}
        # Iterate through all the key-value pairs in the nested dictionary.
        for k2, v2 in v.items():
            new_dict[nk][k2] = v2

    return new_dict


def _read_classification_json(
    index: str, lower: bool = True, data: Union[Optional[optional_pd.DataFrame]] = None
) -> dict:
    """Reads a classification JSON file and returns the data as a dictionary.

    This function reads the "country_data.json" file and returns its contents as a dictionary.
    If the `index` argument is not equal to "regex", the top-level key in the dictionary will be
    changed to the value specified by the `index` argument, and any integer keys in the dictionary
    will be converted from strings to integers. If the `index` argument is equal to "regex", the
    dictionary keys will be compiled as regular expressions.

    Args:
        index (str): The value to be used as the new top-level key in the dictionary. If "regex",
            the keys will be compiled as regular expressions.
        lower (bool): If True, all string values in the dictionary will be converted to lowercase.
        data (optional): A pandas DataFrame containing additional data not contained
            in the "country_data.json" file.

    Returns:
        dict: A dictionary containing with the classification data.
    """

    # Read the JSON file.
    if data is None:
        with open(FILE, "r") as f:
            data = json.load(f)

    # Change the top-level key to the value specified by the `index` argument.
    if index != "regex":
        # Change the top-level key to the value specified by the `index` argument.
        data = _change_top_key_value(index, data, to_lower=lower)
        # Convert any strings to lowercase
        if lower:
            data = _to_lower(data)
        # Convert any integers(-like) to integers
        data = _convert_int(data)

        # if index is ISO2 compile
        if index == "iso2":
            return _compile_regex_keys(data)

        # Convert any integer-like string keys to integers
        return _keys_to_int(data)

    # If the index is "regex". First convert to lower.
    if lower:
        data = _to_lower(data)

    # Second convert any integers(-like) to integers.
    data = _convert_int(data)

    # Then compile the keys as regular expressions.
    return _compile_regex_keys(data)


@dataclass
class ClassificationData:
    """
    A class to represent classification data.

    Attributes:
    source_classification (str): The source classification.
    data (dict): The classification data.

    Methods:
    set_source(source: str): Set the source classification.
    """

    source_classification: str = "regex"
    data: dict = field(default_factory=dict)
    lower: bool = True
    additional_data: Union[optional_pd.DataFrame, None] = None
    data_df: [optional_pd.DataFrame, None] = None

    def __post_init__(self) -> None:
        """Read the classification data from the JSON file"""

        if len(self.data) < 1:
            self.data = _read_classification_json(
                index=self.source_classification, lower=self.lower
            )

        if self.additional_data is not None and isinstance(
            self.additional_data, (optional_pd.DataFrame, str, list[str])
        ):
            self.additional_data = _read_additional_data(self.additional_data)
            self.data = self.data | _read_classification_json(
                data=self.additional_data,
                index=self.source_classification,
                lower=self.lower,
            )

    def __repr__(self) -> str:
        """Return the string representation of the object"""
        return f"{self.__class__.__name__}({self.source_classification})"

    def __str__(self) -> str:
        """Return the string representation of the object"""
        return self.__repr__()

    def get_valid_classifications(self) -> set:
        """Return a list of valid classifications"""
        return _get_unique_keys(self.data)

    def set_source(self, source: str):
        """Set the source classification

        Parameters:
        source (str): New source classification.

        """
        # Return if the source is the same as the current source.
        if source == self.source_classification:
            return
        # Set the new source.
        self.source_classification = source
        # Read the new classification data.
        self.data = _read_classification_json(index=source, lower=self.lower)

        if self.additional_data is not None:
            self.data = self.data | _read_classification_json(
                data=self.additional_data, index=source, lower=self.lower
            )