# AUTOSAR Diagnostics (UDS/OBD)

## Diagnostic Communication Manager (DCM)
The DCM handles UDS (Unified Diagnostic Services, ISO 14229) requests:
- **Service 0x10:** DiagnosticSessionControl (default, extended, programming)
- **Service 0x27:** SecurityAccess (seed-key authentication)
- **Service 0x22/0x2E:** ReadDataByIdentifier / WriteDataByIdentifier
- **Service 0x19:** ReadDTCInformation
- **Service 0x14:** ClearDiagnosticInformation
- **Service 0x31:** RoutineControl
- **Service 0x34-0x37:** Upload/Download (flash programming)

## Diagnostic Event Manager (DEM)
- Stores and manages DTCs (Diagnostic Trouble Codes)
- DTC format: 3-byte code (e.g., U0100 = lost communication with ECM)
- Debouncing strategies: counter-based, time-based
- DTC status byte: testFailed, confirmedDTC, pendingDTC, etc.

## DTC Code Structure
- **P codes:** Powertrain (engine, transmission)
- **C codes:** Chassis (ABS, steering)
- **B codes:** Body (lighting, HVAC, seats)
- **U codes:** Network/Communication
