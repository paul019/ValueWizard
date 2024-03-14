from dataclasses import dataclass
from typing import Union

from domain.uncertainty import _Uncertainty
from domain.value import _Value


@dataclass
class _Result:
    """
    A general-purpose result, i.e. a value that was somehow measured or calculated,
    along with a unit and optional uncertainties (list might be empty).
    """

    name: str
    value: _Value
    unit: str
    uncertainties: list[_Uncertainty]
    sigfigs: Union[int, None]
    decimal_places: Union[int, None]

    def get_total_uncertainty(self) -> _Uncertainty:
        s = 0
        for u in self.uncertainties:
            s += u.uncertainty.get() ** 2
        return _Uncertainty(s**0.5)

    def get_short_result(self) -> "_Result":
        return _Result(
            self.name,
            self.value,
            self.unit,
            [self.get_total_uncertainty()],
            self.sigfigs,
            self.decimal_places,
        )
