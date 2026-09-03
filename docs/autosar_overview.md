# AUTOSAR Overview

AUTOSAR (AUTomotive Open System ARchitecture) is a worldwide development partnership of vehicle manufacturers, suppliers, and other companies from the electronics, semiconductor, and software industries.

## Classic AUTOSAR vs. Adaptive AUTOSAR

### Classic AUTOSAR
- Designed for deeply embedded ECUs with hard real-time constraints
- Static configuration at build time
- OSEK/VDX-based operating system
- Signal-based communication
- Used in: powertrain, chassis, body electronics

### Adaptive AUTOSAR
- Designed for high-performance computing ECUs
- Dynamic configuration and service discovery
- POSIX-based operating system (e.g., Linux)
- Service-oriented communication (SOME/IP, DDS)
- Used in: ADAS, autonomous driving, infotainment

## Key Concepts
- **Software Component (SWC):** atomic unit of software
- **Virtual Function Bus (VFB):** abstraction layer for communication
- **Basic Software (BSW):** standardized modules below the RTE
- **Runtime Environment (RTE):** middleware between SWCs and BSW
- **ECU Extract:** configuration for a specific ECU from the system design
