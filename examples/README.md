# Examples

## `heat_transfer_cooling.py` — natural-convection cooling of stainless steel

A worked engineering example that uses the valuez `Scalar` / `Range` / `Reference`
primitives to hold **source-backed** data, then computes how a hot stainless-steel
part cools in still room air.

### Problem

A solid AISI 304 stainless-steel cube (50 mm side) starts at **300 °C** and cools
in still room air at **25 °C** by **natural (free) convection**. We want the
cooling rate and how long it takes to cool down.

### Ground-truthed inputs

Every input is a `Scalar` or `Range` carrying a `Reference` so it can be traced
back to its source.

Overall / natural-convection heat-transfer coefficient of air, `h` (W/m²·K):

| Value | Source |
| --- | --- |
| 2 – 25 | Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer* (6e), Table 1.1 (free convection, gases) |
| 2.5 – 25 | Standard heat-transfer tables (Air, free convection) |
| 3 – 25 | HVAC Systems Encyclopedia (ingener.by), natural convection, gases |
| ~7 | COMSOL paper — representative computed `h` for natural convection (laminar) |

AISI 304 thermal properties:

| Property | Value | Source |
| --- | --- | --- |
| Density ρ | 8000 kg/m³ | MatWeb 304 SS (8.00 g/cc); thepipingmart SS304 |
| Specific heat cₚ | 500 J/kg·K | MatWeb 304 SS (0–100 °C); AZoM Grade 304 |
| Thermal conductivity k | 16.2 W/m·K | MatWeb 304 SS (0–100 °C) |

### Model

Lumped-capacitance cooling (Newton's law of cooling), valid when the Biot number
`Bi = h·Lc/k < 0.1`:

```
tau  = rho * Lc * cp / h            # cooling time constant [s]
T(t) = T_inf + (T0 - T_inf) * exp(-t / tau)
|dT/dt|_0 = (T0 - T_inf) / tau      # initial cooling rate
Lc   = V / A  (= L/6 for a cube)
```

Radiation is neglected (a reasonable first cut; near 300 °C it would add a few
W/m²·K in parallel and speed cooling somewhat). The `h` **range** is propagated
into a **range** of cooling rates and time constants.

### Run

```bash
# dots (sibling repo) must be importable, e.g.:  pip install -e ../dots
python examples/heat_transfer_cooling.py
```

The script prints an engineering report, persists all inputs and derived values
through `dots` storage, and writes a provenance graph (`provenance.html`) that
links each value to its source. Output goes to `$VALUEZ_EXAMPLE_OUT`
(default: a `valuez_heat_transfer/` folder in your temp directory).

### Representative output (Bi ≈ 0.001–0.013, lumped model valid)

```
Initial cooling rate |dT/dt|_0 : 0.99 to 12.38 K/min   (h = 2 to 25 W/m^2K)
Time constant tau              : 22.2 to 277.8 min
Time to reach 100 degC         : 29 to 361 min
Time to reach 50 degC          : 53 to 666 min
```

## `philosophy_framework.py` — a philosophical framework (Gettier problem)

Shows that the semantic + argument primitives can model a **philosophical
framework** as a traceable graph, not just an engineering dataset.

It encodes the classical analysis of knowledge and Gettier's challenge:

- `Concept`s — `Knowledge`, `JustifiedTrueBelief`, `Belief`, `Truth`, `Justification`.
- `Relation`s over a controlled **predicate vocabulary**
  (`defines`, `presupposes`, `attacks`, ...) with qualifiers — a `modality`
  (`necessary`, `defeasible`, ...) and a `strength` in `[0, 1]`. E.g.
  `JustifiedTrueBelief --presupposes [necessary]--> Justification`.
- `Proposition`s — reified, truth-apt claims (P1, P2, conclusion), each cited.
- `Argument`s — premises ⇒ conclusion (Gettier's reductio; a no-false-lemmas
  rebuttal), with `scheme` labels.
- Argument-level `attacks` relations forming a small Dung-style network:
  `Gettier-Argument attacks JustifiedTrueBelief`, and
  `No-False-Lemmas attacks Gettier-Argument`.

Every claim/relation is ground-truthed via `Reference` (Plato's *Theaetetus*,
Gettier 1963, Clark 1963).

### Run

```bash
python examples/philosophy_framework.py
```

The script prints the framework, persists all values through `dots`, and writes
an interactive **argument map** (`argument_map.html`) wiring premises →
arguments → conclusions plus the attack relations. Output goes to
`$VALUEZ_EXAMPLE_OUT` (default: a `valuez_philosophy/` folder in your temp dir).
