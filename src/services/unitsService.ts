/**
 * SOL-Triad Engine (Preliminary TypeScript Simulator v0.4.1)
 * Unit Registry and Strict Dimensional Verification.
 *
 * Implements exact parity with Python reference kernel (sol_triad/units.py v0.4.1):
 *   - convert(): converts absolute physical values with affine offsets (e.g., 0 °C = 273.15 K).
 *   - convertDelta(): converts additive differences/deltas without affine offsets (e.g., Δ10 °C = 10 K).
 *   - Strict dimensional compatibility (anti-bypass guarantees).
 */

export class DimensionalityError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DimensionalityError";
  }
}

export class UnknownUnitError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UnknownUnitError";
  }
}

export class UnitRegistry {
  public static readonly DIMENSIONS: Record<string, string> = {
    // Pressure
    pa: "pressure",
    kpa: "pressure",
    mpa: "pressure",
    bar: "pressure",
    mbar: "pressure",
    psi: "pressure",
    atm: "pressure",
    torr: "pressure",

    // Time
    s: "time",
    sec: "time",
    ms: "time",
    min: "time",
    hr: "time",
    hour: "time",
    day: "time",

    // Temperature
    c: "temperature",
    celsius: "temperature",
    k: "temperature",
    kelvin: "temperature",
    f: "temperature",
    fahrenheit: "temperature",

    // Ratio / Dimensionless
    ratio: "ratio",
    fraction: "ratio",
    percent: "ratio",
    "%": "ratio",
    ppm: "ratio",

    // Energy
    j: "energy",
    joule: "energy",
    kj: "energy",
    kwh: "energy",
    cal: "energy",
    kcal: "energy",

    // Mass
    kg: "mass",
    g: "mass",
    mg: "mass",
    lb: "mass",

    // Length
    m: "length",
    cm: "length",
    mm: "length",
    km: "length",
    inch: "length",
    ft: "length",

    // Frequency / Rotational
    hz: "frequency",
    khz: "frequency",
    mhz: "frequency",
    rpm: "rotational_speed",
  };

  // Linear conversion factors to base SI units: [multiplier_to_base, offset_to_base]
  // Base SI: Pa, s, K, ratio (1.0), J, kg, m, Hz
  private static readonly CONVERSION_TO_BASE: Record<string, [number, number]> = {
    // Pressure -> Pa
    pa: [1.0, 0.0],
    kpa: [1_000.0, 0.0],
    mpa: [1_000_000.0, 0.0],
    bar: [100_000.0, 0.0],
    mbar: [100.0, 0.0],
    psi: [6894.757293, 0.0],
    atm: [101325.0, 0.0],
    torr: [133.322368, 0.0],

    // Time -> s
    s: [1.0, 0.0],
    sec: [1.0, 0.0],
    ms: [0.001, 0.0],
    min: [60.0, 0.0],
    hr: [3600.0, 0.0],
    hour: [3600.0, 0.0],
    day: [86400.0, 0.0],

    // Temperature -> K
    k: [1.0, 0.0],
    kelvin: [1.0, 0.0],
    c: [1.0, 273.15],
    celsius: [1.0, 273.15],
    f: [5.0 / 9.0, 273.15 - (32.0 * 5.0) / 9.0],
    fahrenheit: [5.0 / 9.0, 273.15 - (32.0 * 5.0) / 9.0],

    // Ratio -> 1.0
    ratio: [1.0, 0.0],
    fraction: [1.0, 0.0],
    percent: [0.01, 0.0],
    "%": [0.01, 0.0],
    ppm: [1e-6, 0.0],

    // Energy -> J
    j: [1.0, 0.0],
    joule: [1.0, 0.0],
    kj: [1000.0, 0.0],
    kwh: [3_600_000.0, 0.0],
    cal: [4.184, 0.0],
    kcal: [4184.0, 0.0],

    // Mass -> kg
    kg: [1.0, 0.0],
    g: [0.001, 0.0],
    mg: [1e-6, 0.0],
    lb: [0.45359237, 0.0],

    // Length -> m
    m: [1.0, 0.0],
    cm: [0.01, 0.0],
    mm: [0.001, 0.0],
    km: [1000.0, 0.0],
    inch: [0.0254, 0.0],
    ft: [0.3048, 0.0],

    // Frequency -> Hz
    hz: [1.0, 0.0],
    khz: [1000.0, 0.0],
    mhz: [1_000_000.0, 0.0],
    rpm: [1.0 / 60.0, 0.0],
  };

  public static normalizeUnit(unit?: string | null): string | null {
    if (unit === null || unit === undefined) return null;
    const trimmed = unit.trim().toLowerCase();
    return trimmed.length > 0 ? trimmed : null;
  }

  public static getDimension(unit?: string | null): string | null {
    const u = this.normalizeUnit(unit);
    if (!u) return null;
    return this.DIMENSIONS[u] ?? null;
  }

  public static isKnown(unit?: string | null): boolean {
    const u = this.normalizeUnit(unit);
    if (!u) return false;
    return u in this.DIMENSIONS;
  }

  /**
   * Strict compatibility check.
   * Anti-bypass rules matching sol_triad/units.py:
   *   - If one is missing and the other is specified -> false (reject asymmetric bypass)
   *   - If both are unrecognized -> false (unknown units cannot match each other)
   *   - If dimensions differ -> false
   *   - If both are empty -> true only if allowBothEmpty is true.
   */
  public static areCompatible(
    unit1?: string | null,
    unit2?: string | null,
    allowBothEmpty: boolean = true
  ): [boolean, string] {
    const u1 = this.normalizeUnit(unit1);
    const u2 = this.normalizeUnit(unit2);

    if (u1 === null && u2 === null) {
      if (allowBothEmpty) {
        return [true, "Both parameters are unitless."];
      }
      return [false, "Missing units for both parameters in strict dimensional context."];
    }

    if ((u1 === null && u2 !== null) || (u1 !== null && u2 === null)) {
      return [false, `Asymmetric unit specification: '${unit1}' vs '${unit2}'. Missing unit bypass rejected.`];
    }

    const dim1 = this.getDimension(u1);
    const dim2 = this.getDimension(u2);

    if (dim1 === null && dim2 === null) {
      return [false, `Both units '${unit1}' and '${unit2}' are unknown to UnitRegistry.`];
    }
    if (dim1 === null) {
      return [false, `Unit '${unit1}' is not recognized in UnitRegistry.`];
    }
    if (dim2 === null) {
      return [false, `Unit '${unit2}' is not recognized in UnitRegistry.`];
    }

    if (dim1 !== dim2) {
      return [false, `Dimensional incompatibility: '${unit1}' (${dim1}) cannot be reconciled with '${unit2}' (${dim2}).`];
    }

    return [true, `Units '${unit1}' and '${unit2}' are dimensionally compatible (${dim1}).`];
  }

  /**
   * Converts absolute numerical value between dimensionally compatible units.
   * Includes affine offset (e.g. 0 °C = 273.15 K).
   * Used for state values, protected values, min/max bounds.
   */
  public static convert(value: number, fromUnit: string, toUnit: string): number {
    if (isNaN(value) || !isFinite(value)) {
      throw new Error(`Cannot convert non-finite float value: ${value}`);
    }

    const uFrom = this.normalizeUnit(fromUnit);
    const uTo = this.normalizeUnit(toUnit);

    if (!uFrom || !(uFrom in this.CONVERSION_TO_BASE)) {
      throw new UnknownUnitError(`Unknown source unit: '${fromUnit}'`);
    }
    if (!uTo || !(uTo in this.CONVERSION_TO_BASE)) {
      throw new UnknownUnitError(`Unknown destination unit: '${toUnit}'`);
    }

    const dimFrom = this.getDimension(uFrom);
    const dimTo = this.getDimension(uTo);
    if (dimFrom !== dimTo) {
      throw new DimensionalityError(
        `Cannot convert between different dimensions: '${fromUnit}' (${dimFrom}) -> '${toUnit}' (${dimTo})`
      );
    }

    if (uFrom === uTo) {
      return value;
    }

    const [multFrom, offsetFrom] = this.CONVERSION_TO_BASE[uFrom];
    const baseVal = value * multFrom + offsetFrom;

    const [multTo, offsetTo] = this.CONVERSION_TO_BASE[uTo];
    return (baseVal - offsetTo) / multTo;
  }

  /**
   * Converts an additive difference/delta WITHOUT applying affine offsets.
   * Delta scaling: Δy = Δx * multFrom / multTo.
   * Used for state_delta and temperature-valued resource_cost.
   * Example: convertDelta(10, "c", "k") = 10.0 (NOT 283.15 K).
   */
  public static convertDelta(value: number, fromUnit: string, toUnit: string): number {
    if (isNaN(value) || !isFinite(value)) {
      throw new Error(`Cannot convert non-finite float value: ${value}`);
    }

    const uFrom = this.normalizeUnit(fromUnit);
    const uTo = this.normalizeUnit(toUnit);

    if (!uFrom || !(uFrom in this.CONVERSION_TO_BASE)) {
      throw new UnknownUnitError(`Unknown source unit: '${fromUnit}'`);
    }
    if (!uTo || !(uTo in this.CONVERSION_TO_BASE)) {
      throw new UnknownUnitError(`Unknown destination unit: '${toUnit}'`);
    }

    const dimFrom = this.getDimension(uFrom);
    const dimTo = this.getDimension(uTo);
    if (dimFrom !== dimTo) {
      throw new DimensionalityError(
        `Cannot convert between different dimensions: '${fromUnit}' (${dimFrom}) -> '${toUnit}' (${dimTo})`
      );
    }

    const [multFrom] = this.CONVERSION_TO_BASE[uFrom];
    const [multTo] = this.CONVERSION_TO_BASE[uTo];
    return (value * multFrom) / multTo;
  }
}
