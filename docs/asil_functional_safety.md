# ASIL and Functional Safety (ISO 26262)

## ASIL Classification
ASIL (Automotive Safety Integrity Level) classifies the safety risk of vehicle functions:

| ASIL | Severity | Probability | Controllability | Example |
|------|----------|-------------|-----------------|---------|
| QM   | -        | -           | -               | Infotainment |
| A    | Low      | Low         | High            | Rear lights |
| B    | Medium   | Medium      | Medium          | Headlights |
| C    | High     | Medium      | Low             | ABS |
| D    | Critical | High        | Low             | Steering, Airbags |

## ASIL Decomposition
A higher ASIL can be decomposed into two lower ASILs on redundant elements:
- ASIL D = ASIL C(D) + ASIL A(D)
- ASIL D = ASIL B(D) + ASIL B(D)
- Requires independence between elements (no common-cause failures)

## Key Safety Concepts
- **Safety Goal:** top-level safety requirement (e.g., "prevent unintended acceleration")
- **Functional Safety Concept:** system-level allocation of safety goals to functions
- **Technical Safety Concept:** HW/SW-level realization of safety requirements
- **Freedom from Interference (FFI):** QM software must not corrupt ASIL software
- **Dependent Failure Analysis:** common-cause and cascading failure analysis

## Software Measures by ASIL

| Measure | QM | A | B | C | D |
|---------|----|----|----|----|-----|
| Code review | + | ++ | ++ | ++ | ++ |
| Static analysis | o | + | ++ | ++ | ++ |
| Unit testing | + | ++ | ++ | ++ | ++ |
| MC/DC coverage | o | o | + | ++ | ++ |
| Back-to-back testing | o | o | + | ++ | ++ |

Legend: o = optional, + = recommended, ++ = highly recommended
