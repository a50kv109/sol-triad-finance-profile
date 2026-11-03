"""
Модульные тесты UnitRegistry и физических размерностей.
"""

from sol_triad_core import (
    UnitRegistry,
    UnknownUnitError,
    DimensionalityError,
)


def test_recognized_dimensions():
    assert UnitRegistry.get_dimension("bar") == "pressure"
    assert UnitRegistry.get_dimension("psi") == "pressure"
    assert UnitRegistry.get_dimension("sec") == "time"
    assert UnitRegistry.get_dimension("ms") == "time"
    assert UnitRegistry.get_dimension("celsius") == "temperature"
    assert UnitRegistry.get_dimension("kelvin") == "temperature"
    assert UnitRegistry.get_dimension("joule") == "energy"
    assert UnitRegistry.get_dimension("volt") == "voltage"


def test_unknown_units_not_compatible():
    compat, msg = UnitRegistry.are_compatible("flurps", "glorps")
    assert compat is False
    assert "not recognized" in msg.lower() or "unknown" in msg.lower()


def test_asymmetric_unit_specification_fails():
    compat, msg = UnitRegistry.are_compatible(None, "bar")
    assert compat is False
    assert "asymmetric" in msg.lower()


def test_incompatible_dimensions_fail():
    compat, msg = UnitRegistry.are_compatible("bar", "sec")
    assert compat is False
    assert "incompatibility" in msg.lower()


def test_unit_conversions():
    # Pressure
    val_psi = UnitRegistry.convert(1.0, "bar", "psi")
    assert abs(val_psi - 14.50377) < 1e-3

    # Time
    assert UnitRegistry.convert(2.5, "sec", "ms") == 2500.0
    assert UnitRegistry.convert(120.0, "sec", "min") == 2.0

    # Temperature (affine)
    assert abs(UnitRegistry.convert(0.0, "celsius", "kelvin") - 273.15) < 1e-4
    assert abs(UnitRegistry.convert(100.0, "celsius", "kelvin") - 373.15) < 1e-4


if __name__ == "__main__":
    test_recognized_dimensions()
    test_unknown_units_not_compatible()
    test_asymmetric_unit_specification_fails()
    test_incompatible_dimensions_fail()
    test_unit_conversions()
    print("test_units.py: ALL TESTS PASSED")
