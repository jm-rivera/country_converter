import pathlib

from country_converter_package.country_converter import *


class PandasNotInstalled:
    def __getattr__(self, name):
        return None


def _check_pandas():
    try:
        import pandas as optional_pd

        try:
            optional_pd.__version__
        except AttributeError:
            return PandasNotInstalled()
        return optional_pd
    except ModuleNotFoundError:
        return PandasNotInstalled()


from .version import __version__

FILE = pathlib.Path(__file__).resolve().parent / "country_data.json"

__author__ = "Konstantin Stadler"
__all__ = ["agg_conc", "match", "convert", "CountryConverter", "cli_output"]
