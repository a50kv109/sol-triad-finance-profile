"""
Реестр физических размерностей и конверсии величин SOL-Triad Core.
"""

from typing import Dict, Tuple, Optional


class UnitRegistryError(Exception):
    """Базовое исключение реестра размерностей."""
    pass


class UnknownUnitError(UnitRegistryError):
    """Исключение при обращении к неизвестной единице измерения."""
    pass


class DimensionalityError(UnitRegistryError):
    """Исключение при несовместимости физических размерностей."""
    pass


class UnitRegistry:
    """
    Нормализованный реестр размерностей.
    Поддерживает: pressure, time, temperature, ratio, energy, mass, length, frequency, speed.
    """

    # Таблица соответствия единиц и базовых размерностей
    _UNIT_TO_DIMENSION: Dict[str, str] = {
        # Pressure (Base: Pa)
        "pa": "pressure",
        "kpa": "pressure",
        "mpa": "pressure",
        "bar": "pressure",
        "mbar": "pressure",
        "psi": "pressure",
        "atm": "pressure",
        # Time (Base: sec)
        "sec": "time",
        "s": "time",
        "ms": "time",
        "min": "time",
        "hr": "time",
        # Temperature (Base: kelvin)
        "kelvin": "temperature",
        "k": "temperature",
        "celsius": "temperature",
        "c": "temperature",
        # Ratio (Base: dimensionless fraction 0..1)
        "fraction": "ratio",
        "percent": "ratio",
        "%": "ratio",
        "ratio": "ratio",
        # Energy (Base: joule)
        "joule": "energy",
        "j": "energy",
        "kj": "energy",
        "kwh": "energy",
        # Mass (Base: kg)
        "kg": "mass",
        "g": "mass",
        "mg": "mass",
        # Length (Base: meter)
        "meter": "length",
        "m": "length",
        "km": "length",
        "mm": "length",
        # Voltage / Electric Potential (Base: volt)
        "volt": "voltage",
        "v": "voltage",
        "kv": "voltage",
        "mv": "voltage",
        # Currency / Abstract Funds (Base: standard unit)
        "currency_unit": "currency",
        "usd": "currency",
        "eur": "currency",
        "rub": "currency",
        "gbp": "currency",
    }

    # Масштабные коэффициенты к базовым единицам СИ (x * factor = base)
    _SCALE_TO_BASE: Dict[str, float] = {
        # Pressure -> Pa
        "pa": 1.0,
        "kpa": 1000.0,
        "mpa": 1000000.0,
        "bar": 100000.0,
        "mbar": 100.0,
        "psi": 6894.757,
        "atm": 101325.0,
        # Time -> sec
        "sec": 1.0,
        "s": 1.0,
        "ms": 0.001,
        "min": 60.0,
        "hr": 3600.0,
        # Ratio -> fraction
        "fraction": 1.0,
        "ratio": 1.0,
        "percent": 0.01,
        "%": 0.01,
        # Energy -> joule
        "joule": 1.0,
        "j": 1.0,
        "kj": 1000.0,
        "kwh": 3600000.0,
        # Mass -> kg
        "kg": 1.0,
        "g": 0.001,
        "mg": 0.000001,
        # Length -> meter
        "meter": 1.0,
        "m": 1.0,
        "km": 1000.0,
        "mm": 0.001,
        # Voltage -> volt
        "volt": 1.0,
        "v": 1.0,
        "kv": 1000.0,
        "mv": 0.001,
        # Currency
        "currency_unit": 1.0,
        "usd": 1.0,
        "eur": 1.0,
        "rub": 1.0,
        "gbp": 1.0,
    }

    @classmethod
    def get_dimension(cls, unit: str) -> str:
        """Возвращает физическую размерность единицы измерения."""
        norm_unit = unit.strip().lower()
        if norm_unit not in cls._UNIT_TO_DIMENSION:
            raise UnknownUnitError(f"Unit '{unit}' is not recognized in registry.")
        return cls._UNIT_TO_DIMENSION[norm_unit]

    @classmethod
    def are_compatible(cls, unit_a: Optional[str], unit_b: Optional[str]) -> Tuple[bool, str]:
        """
        Проверяет размерную совместимость двух единиц.
        Анти-байпас: если одна единица указана, а другая нет — несовместимы.
        Если обе не указаны — совместимы (безразмерные).
        """
        if unit_a is None and unit_b is None:
            return True, "Both dimensionless"
        if (unit_a is None) != (unit_b is None):
            return False, f"Asymmetric unit specification: {unit_a} vs {unit_b}"
        
        try:
            dim_a = cls.get_dimension(unit_a)  # type: ignore
            dim_b = cls.get_dimension(unit_b)  # type: ignore
        except UnknownUnitError as e:
            return False, str(e)

        if dim_a != dim_b:
            return False, f"Dimensional incompatibility: '{unit_a}' ({dim_a}) != '{unit_b}' ({dim_b})"
        return True, "Compatible"

    @classmethod
    def convert(cls, value: float, from_unit: Optional[str], to_unit: Optional[str]) -> float:
        """
        Выполняет точную детерминированную конверсию величины между совместимыми единицами.
        """
        if from_unit is None and to_unit is None:
            return value
        if from_unit is None or to_unit is None:
            raise DimensionalityError(f"Cannot convert between asymmetric units: {from_unit} and {to_unit}")

        norm_from = from_unit.strip().lower()
        norm_to = to_unit.strip().lower()

        if norm_from == norm_to:
            return value

        dim_from = cls.get_dimension(norm_from)
        dim_to = cls.get_dimension(norm_to)

        if dim_from != dim_to:
            raise DimensionalityError(
                f"Incompatible dimensions: cannot convert '{from_unit}' ({dim_from}) to '{to_unit}' ({dim_to})"
            )

        # Специальная обработка аффинных шкал (температура)
        if dim_from == "temperature":
            # Сначала в Кельвины
            val_kelvin = (value + 273.15) if norm_from in ("celsius", "c") else value
            # Из Кельвинов в целевую
            return (val_kelvin - 273.15) if norm_to in ("celsius", "c") else val_kelvin

        # Линейное масштабирование через базовую величину
        factor_from = cls._SCALE_TO_BASE[norm_from]
        factor_to = cls._SCALE_TO_BASE[norm_to]

        val_base = value * factor_from
        return val_base / factor_to
