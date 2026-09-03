# Over-the-Air (OTA) Software Updates

## OTA Architecture
- **Backend Server:** campaign management, binary distribution
- **Telematics Control Unit (TCU):** vehicle-side OTA client
- **Central Gateway:** distributes updates to target ECUs
- **Target ECUs:** receive and install software updates

## Update Process
1. **Campaign creation:** select vehicles, validate compatibility
2. **Download:** TCU downloads package via cellular/WiFi
3. **Validation:** verify signature, check prerequisites
4. **Installation:** flash target ECU (A/B partition or direct)
5. **Verification:** ECU self-test, version confirmation
6. **Reporting:** status reported back to backend

## Safety Considerations
- **Dual-bank (A/B):** always keep a working fallback partition
- **Rollback:** automatic if self-test fails after update
- **Drive-ready check:** never update safety ECUs while driving
- **Voltage monitoring:** abort if battery below threshold
- **Integrity:** cryptographic signature verification (X.509)

## UNECE WP.29 / R156 Requirements
- Secure update process (end-to-end encryption)
- Update management system certification
- Version tracking and rollback capability
- User notification and consent
