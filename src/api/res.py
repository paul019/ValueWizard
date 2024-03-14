from typing import Union, List, Tuple
from plum import dispatch, overload

from api.printable_result import PrintableResult
from application.cache import _res_cache
from application.rounder import _Rounder
from application.helpers import _Helpers
from domain.result import _Result
from domain.value import _Value
from domain.uncertainty import _Uncertainty


# TODO: import types from typing to ensure backwards compatibility down to Python 3.8

# TODO: use pydantic instead of manual and ugly type checking
# see: https://docs.pydantic.dev/latest/
# This way we can code as if the happy path is the only path, and let pydantic
# handle the error checking and reporting.


@overload
def res(
    name: str,
    value: Union[float, str],
    unit: str = "",
    sigfigs: Union[int, None] = None,
    decimal_places: Union[int, None] = None,
) -> PrintableResult:
    return res(name, value, [], unit, sigfigs, decimal_places)


@overload
def res(
    name: str,
    value: Union[float, str],
    uncert: Union[
        float,
        str,
        Tuple[Union[float, str], str],
        List[Union[float, str, Tuple[Union[float, str], str]]],
        None
    ] = None,
    sigfigs: Union[int, None] = None,
    decimal_places: Union[int, None] = None,
) -> PrintableResult:
    return res(name, value, uncert, "", sigfigs, decimal_places)


@overload
def res(
    name: str,
    value: Union[float, str],
    sigfigs: Union[int, None] = None,
    decimal_places: Union[int, None] = None,
) -> PrintableResult:
    return res(name, value, [], "", sigfigs, decimal_places)


@overload
def res(
    name: str,
    value: Union[float, str],
    sys: float,
    stat: float,
    unit: str = "",
    sigfigs: Union[int, None] = None,
    decimal_places: Union[int, None] = None,
) -> PrintableResult:
    return res(name, value, [(sys, "sys"), (stat, "stat")], unit, sigfigs, decimal_places)


@overload
def res(
    name: str,
    value: Union[float, str],
    uncert: Union[
        float,
        str,
        Tuple[Union[float, str], str],
        List[Union[float, str, Tuple[Union[float, str], str]]],
        None
    ] = None,
    unit: str = "",
    sigfigs: Union[int, None] = None,
    decimal_places: Union[int, None] = None,
) -> PrintableResult:
    if uncert is None:
        uncert = []

    # Parse user input
    name_res = _parse_name(name)
    value_res = _parse_value(value)
    uncertainties_res = _parse_uncertainties(uncert)
    unit_res = _parse_unit(unit)
    sigfigs_res = _parse_sigfigs(sigfigs)
    decimal_places_res = _parse_decimal_places(decimal_places)

    # Assemble the result
    result = _Result(
        name_res, value_res, unit_res, uncertainties_res, sigfigs_res, decimal_places_res
    )
    _Rounder.round_result(result)
    _res_cache.add(name, result)

    return PrintableResult(result)


# Hack for method "overloading" in Python
# see https://beartype.github.io/plum/integration.html
# This is a good writeup: https://stackoverflow.com/a/29091980/
@dispatch
def res(*args, **kwargs) -> object:
    # This method only scans for all `overload`-decorated methods
    # and properly adds them as Plum methods.
    pass


def _check_if_number_string(value: str) -> None:
    """Raises a ValueError if the string is not a valid number."""
    try:
        float(value)
    except ValueError as exc:
        raise ValueError(f"String value must be a valid number, not {value}") from exc


def _parse_name(name: str) -> str:
    """Parses the name."""
    if not isinstance(name, str):
        raise TypeError(f"`name` must be a string, not {type(name)}")

    name = (
        name.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("Ä", "Ae")
        .replace("Ö", "Oe")
        .replace("Ü", "Ue")
        .replace("ß", "ss")
    )

    parsed_name = ""
    next_chat_upper = False

    for char in name:
        if char.isalpha():
            if next_chat_upper:
                parsed_name += char.upper()
                next_chat_upper = False
            else:
                parsed_name += char
        elif char.isdigit():
            digit = _Helpers.number_to_word(int(char))
            if parsed_name == "":
                parsed_name += digit
            else:
                parsed_name += digit[0].upper() + digit[1:]
            next_chat_upper = True
        elif char in [" ", "_", "-"]:
            next_chat_upper = True

    return parsed_name


def _parse_unit(unit: str) -> str:
    """Parses the unit."""
    if not isinstance(unit, str):
        raise TypeError(f"`unit` must be a string, not {type(unit)}")

    # TODO: maybe add some basic checks to catch siunitx errors, e.g.
    # unsupported symbols etc. But maybe leave this to LaTeX and just return
    # the LaTeX later on. But catching it here would be more user-friendly,
    # as the user would get immediate feedback and not only once they try to
    # export the results.
    return unit


def _parse_sigfigs(sigfigs: Union[int, None]) -> Union[int, None]:
    """Parses the number of sigfigs."""
    if sigfigs is None:
        return None

    if not isinstance(sigfigs, int):
        raise TypeError(f"`sigfigs` must be an int, not {type(sigfigs)}")

    if sigfigs < 1:
        raise ValueError("`sigfigs` must be positive")

    return sigfigs


def _parse_decimal_places(decimal_places: Union[int, None]) -> Union[int, None]:
    """Parses the number of sigfigs."""
    if decimal_places is None:
        return None

    if not isinstance(decimal_places, int):
        raise TypeError(f"`decimal_places` must be an int, not {type(decimal_places)}")

    if decimal_places < 0:
        raise ValueError("`decimal_places` must be non-negative")

    return decimal_places


def _parse_value(value: Union[float, str]) -> _Value:
    """Converts the value to a _Value object."""
    if not isinstance(value, (float, str)):
        raise TypeError(f"`value` must be a float or string, not {type(value)}")

    if isinstance(value, str):
        _check_if_number_string(value)

    return _Value(value)


def _parse_uncertainties(
    uncertainties: Union[
        float,
        str,
        Tuple[Union[float, str], str],
        List[Union[float, str, Tuple[Union[float, str], str]]],
    ]
) -> List[_Uncertainty]:
    """Converts the uncertainties to a list of _Uncertainty objects."""
    uncertainties_res = []

    # no list, but a single value was given
    if isinstance(uncertainties, (float, str, Tuple)):
        uncertainties = [uncertainties]

    assert isinstance(uncertainties, List)

    for uncert in uncertainties:
        if isinstance(uncert, (float, str)):
            if isinstance(uncert, str):
                _check_if_number_string(uncert)
                if float(uncert) <= 0:
                    raise ValueError("Uncertainty must be positive.")
            uncertainties_res.append(_Uncertainty(uncert))

        elif isinstance(uncert, Tuple):
            if not isinstance(uncert[0], (float, str)):
                raise TypeError(
                    f"First argument of uncertainty-tuple must be a float or a string, not {type(uncert[0])}"
                )
            if isinstance(uncert[0], str):
                _check_if_number_string(uncert[0])
            uncertainties_res.append(_Uncertainty(uncert[0], _parse_name(uncert[1])))

        else:
            raise TypeError(f"Each uncertainty must be a tuple or a float/str, not {type(uncert)}")

    return uncertainties_res
