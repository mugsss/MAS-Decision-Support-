# Software Versioning in Automotive

## Version Numbering
Format: `SW-{major}.{minor}.{patch}`
- **Major:** architectural changes, breaking interface changes
- **Minor:** new features, backward-compatible changes
- **Patch:** bug fixes, calibration updates

## Software Baseline
A baseline is a frozen set of SW versions for all ECUs in a vehicle:
```
Baseline BL-2025-Q3-R2:
  BCM:         SW-3.12.7
  TCU:         SW-2.8.14
  ADAS_Front:  SW-5.1.3
  GW_Central:  SW-4.6.0
  ...
```

## Version Management Rules
1. Each ECU has exactly one active SW version
2. SW version must match the approved baseline for the project phase
3. Deviations from baseline require a change request
4. Previous versions must be archived and recoverable
5. Part number links HW variant to compatible SW versions

## Compatibility Matrix
- HW version ↔ SW version compatibility
- Inter-ECU SW version compatibility
- Tool chain version requirements
- Calibration data version alignment
