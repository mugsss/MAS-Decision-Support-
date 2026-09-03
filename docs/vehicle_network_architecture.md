# Vehicle Network Architecture

## Bus Systems
### CAN (Controller Area Network)
- Speed: 500 kbps (CAN-HS) / 125 kbps (CAN-LS)
- CAN FD: up to 8 Mbps data phase
- Topology: linear bus with termination
- Use: powertrain, chassis, body

### LIN (Local Interconnect Network)
- Speed: up to 20 kbps
- Master-slave architecture
- Use: sensors, actuators (seat, mirror, window)

### FlexRay
- Speed: 10 Mbps per channel (dual-channel)
- Time-triggered + event-triggered
- Use: safety-critical chassis systems (steer-by-wire)

### Automotive Ethernet
- Speed: 100 Mbps (100BASE-T1) / 1 Gbps (1000BASE-T1)
- Full-duplex, point-to-point or switched
- Use: ADAS, cameras, infotainment, diagnostics

## Gateway ECU
The central gateway routes messages between bus systems:
- CAN ↔ CAN translation
- CAN ↔ Ethernet bridging
- Security gateway (OBD port firewall)
- Diagnostic routing (target ECU addressing)

## Network Management (AUTOSAR)
- **NM (Network Management):** coordinates sleep/wakeup
- Each ECU sends periodic NM messages while awake
- Coordinated shutdown: all ECUs agree before sleeping
- Partial networking: only wake relevant ECUs
