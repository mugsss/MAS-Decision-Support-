"""
Synthetic data generator for the Automotive MAS.
Generates: PDM vehicle data, integration logs, fleet SQLite DB,
           empty memory DB, and RAG markdown documents.

Usage: python setup_data.py
"""

import json
import random
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ECU_TYPES = [
    "BCM", "TCU", "ADAS_Front", "ADAS_Rear", "HMI_Cluster",
    "GW_Central", "EPS", "ABS_ESC", "HVAC", "BMS",
    "PDC", "Camera_Front", "Camera_Rear", "Radar_Front", "Lidar_Top",
]

PART_PREFIX = "7PP-"
SW_PREFIX = "SW-"

DTC_CODES = [
    "U0100", "U0073", "U0121", "U0140", "U0155",
    "P0562", "P0606", "P0700", "P2544", "P0300",
    "C0035", "C0040", "C0050", "C0060", "C0070",
    "B1000", "B1015", "B1200", "B1325", "B1400",
]

SEVERITY_LEVELS = ["INFO", "WARNING", "ERROR", "CRITICAL"]
LOG_SOURCES = ["CAN_BUS", "DIAG_SESSION", "FLASH_TOOL", "OTA_SERVICE", "TEST_BENCH"]

VEHICLE_PLATFORMS = ["MQB-Evo", "MEB", "PPE", "SSP"]
TEST_TYPES = ["flash_test", "integration_test", "regression_test", "e2e_test", "smoke_test"]
TEST_RESULTS = ["pass", "fail", "blocked", "skipped"]
DEFECT_SEVERITIES = ["critical", "major", "minor", "trivial"]
DEFECT_STATUSES = ["open", "in_progress", "resolved", "closed"]


def generate_pdm_vehicles(count: int = 10) -> list[dict]:
    vehicles = []
    for i in range(1, count + 1):
        vehicle_id = f"VIN-{i:04d}-TEST"
        platform = random.choice(VEHICLE_PLATFORMS)
        num_ecus = random.randint(6, 12)
        chosen_ecus = random.sample(ECU_TYPES, num_ecus)

        ecus = []
        for ecu_name in chosen_ecus:
            ecu_id = f"{vehicle_id}-{ecu_name}"
            part_number = f"{PART_PREFIX}{random.randint(900, 999)}-{random.randint(100, 999)}-{chr(random.randint(65, 90))}"
            sw_major = random.randint(1, 5)
            sw_minor = random.randint(0, 20)
            sw_patch = random.randint(0, 50)
            ecus.append({
                "ecu_id": ecu_id,
                "ecu_type": ecu_name,
                "part_number": part_number,
                "hw_version": f"HW-{random.randint(1, 3)}.{random.randint(0, 5)}",
                "sw_version": f"{SW_PREFIX}{sw_major}.{sw_minor}.{sw_patch}",
                "supplier": random.choice(["Bosch", "Continental", "ZF", "Denso", "Aptiv", "Valeo"]),
                "last_flashed": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
            })

        vehicles.append({
            "vehicle_id": vehicle_id,
            "platform": platform,
            "model_year": random.choice([2024, 2025, 2026]),
            "project_code": f"PRJ-{platform}-{random.randint(100, 999)}",
            "ecus": ecus,
        })
    return vehicles


def generate_integration_logs(vehicles: list[dict], count: int = 200) -> list[dict]:
    logs = []
    base_time = datetime.now() - timedelta(days=30)

    for i in range(count):
        vehicle = random.choice(vehicles)
        ecu = random.choice(vehicle["ecus"])
        severity = random.choices(
            SEVERITY_LEVELS, weights=[40, 30, 20, 10], k=1
        )[0]

        timestamp = base_time + timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        entry = {
            "log_id": f"LOG-{i + 1:05d}",
            "timestamp": timestamp.isoformat(),
            "vehicle_id": vehicle["vehicle_id"],
            "ecu_id": ecu["ecu_id"],
            "ecu_type": ecu["ecu_type"],
            "severity": severity,
            "source": random.choice(LOG_SOURCES),
        }

        if severity in ("ERROR", "CRITICAL"):
            entry["dtc_code"] = random.choice(DTC_CODES)
            entry["message"] = _generate_error_message(ecu["ecu_type"], entry["dtc_code"])
        elif severity == "WARNING":
            entry["message"] = _generate_warning_message(ecu["ecu_type"])
        else:
            entry["message"] = _generate_info_message(ecu["ecu_type"])

        if random.random() < 0.15:
            entry["can_error"] = random.choice(["bus_off", "error_passive", "stuff_error", "crc_error"])

        logs.append(entry)

    logs.sort(key=lambda x: x["timestamp"])
    return logs


def _generate_error_message(ecu_type: str, dtc: str) -> str:
    templates = [
        f"{ecu_type}: DTC {dtc} — communication timeout on internal bus",
        f"{ecu_type}: Flash sequence aborted, DTC {dtc} set",
        f"{ecu_type}: Diagnostic session rejected (DTC {dtc}), security access failed",
        f"{ecu_type}: Watchdog reset detected, DTC {dtc}",
        f"{ecu_type}: CAN message missing for >500ms, DTC {dtc} stored",
    ]
    return random.choice(templates)


def _generate_warning_message(ecu_type: str) -> str:
    templates = [
        f"{ecu_type}: SW version mismatch with baseline — update recommended",
        f"{ecu_type}: Intermittent CAN frame drop (rate 0.{random.randint(1, 9)}%)",
        f"{ecu_type}: Memory utilization at {random.randint(75, 95)}%",
        f"{ecu_type}: Response time degraded ({random.randint(50, 200)}ms vs. 30ms nominal)",
        f"{ecu_type}: Pending calibration data not yet applied",
    ]
    return random.choice(templates)


def _generate_info_message(ecu_type: str) -> str:
    templates = [
        f"{ecu_type}: Flash completed successfully",
        f"{ecu_type}: Diagnostic session opened (extended session)",
        f"{ecu_type}: Self-test passed — all internal checks OK",
        f"{ecu_type}: SW version verified against baseline",
        f"{ecu_type}: CAN gateway routing table updated",
    ]
    return random.choice(templates)


def generate_fleet_db(vehicles: list[dict], db_path: Path):
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE vehicles (
            vehicle_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            model_year INTEGER NOT NULL,
            project_code TEXT NOT NULL,
            ecu_count INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE integration_runs (
            run_id TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL REFERENCES vehicles(vehicle_id),
            run_type TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            total_tests INTEGER NOT NULL DEFAULT 0,
            passed INTEGER NOT NULL DEFAULT 0,
            failed INTEGER NOT NULL DEFAULT 0,
            blocked INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE test_results (
            test_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES integration_runs(run_id),
            test_name TEXT NOT NULL,
            test_type TEXT NOT NULL,
            result TEXT NOT NULL,
            duration_ms INTEGER,
            ecu_type TEXT,
            error_message TEXT,
            executed_at TEXT NOT NULL
        );

        CREATE TABLE defects (
            defect_id TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL REFERENCES vehicles(vehicle_id),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL,
            ecu_type TEXT,
            dtc_code TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    # --- vehicles (extend the 10 PDM vehicles to 500 for fleet analytics) ---
    base_time = datetime.now() - timedelta(days=180)
    all_vehicle_ids = []

    for v in vehicles:
        cur.execute(
            "INSERT INTO vehicles VALUES (?, ?, ?, ?, ?, ?)",
            (v["vehicle_id"], v["platform"], v["model_year"],
             v["project_code"], len(v["ecus"]),
             (base_time + timedelta(days=random.randint(0, 30))).isoformat()),
        )
        all_vehicle_ids.append(v["vehicle_id"])

    for i in range(len(vehicles) + 1, 501):
        vid = f"VIN-{i:04d}-FLEET"
        platform = random.choice(VEHICLE_PLATFORMS)
        cur.execute(
            "INSERT INTO vehicles VALUES (?, ?, ?, ?, ?, ?)",
            (vid, platform, random.choice([2024, 2025, 2026]),
             f"PRJ-{platform}-{random.randint(100, 999)}",
             random.randint(6, 15),
             (base_time + timedelta(days=random.randint(0, 120))).isoformat()),
        )
        all_vehicle_ids.append(vid)

    # --- integration_runs (500) ---
    run_ids = []
    for i in range(1, 501):
        run_id = f"RUN-{i:05d}"
        run_ids.append(run_id)
        vid = random.choice(all_vehicle_ids)
        started = base_time + timedelta(days=random.randint(0, 170), hours=random.randint(0, 23))
        duration = timedelta(minutes=random.randint(5, 120))
        total = random.randint(10, 100)
        passed = int(total * random.uniform(0.6, 1.0))
        failed = random.randint(0, total - passed)
        blocked = total - passed - failed
        status = "pass" if failed == 0 and blocked == 0 else "fail"

        cur.execute(
            "INSERT INTO integration_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, vid, random.choice(TEST_TYPES),
             started.isoformat(), (started + duration).isoformat(),
             status, total, passed, failed, blocked),
        )

    # --- test_results (500) ---
    test_names = [
        "CAN_comm_check", "flash_sequence", "diag_session_open",
        "security_access", "ecu_reset", "read_dtc", "clear_dtc",
        "calibration_verify", "gateway_routing", "sleep_wakeup",
        "ota_update_verify", "memory_check", "watchdog_test",
        "voltage_monitor", "bus_off_recovery",
    ]

    for i in range(1, 501):
        run_id = random.choice(run_ids)
        result = random.choices(TEST_RESULTS, weights=[60, 20, 10, 10], k=1)[0]
        executed = base_time + timedelta(days=random.randint(0, 170), hours=random.randint(0, 23))
        error_msg = None
        if result == "fail":
            error_msg = f"Assertion failed: expected OK, got TIMEOUT on step {random.randint(1, 10)}"

        cur.execute(
            "INSERT INTO test_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"TEST-{i:05d}", run_id, random.choice(test_names),
             random.choice(TEST_TYPES), result,
             random.randint(100, 30000),
             random.choice(ECU_TYPES), error_msg,
             executed.isoformat()),
        )

    # --- defects (200) ---
    defect_titles = [
        "CAN timeout on {ecu} during flash",
        "{ecu} security access rejected intermittently",
        "DTC {dtc} stored after cold start",
        "{ecu} SW version rollback after OTA",
        "Watchdog reset loop on {ecu}",
        "Gateway routing incorrect for {ecu}",
        "{ecu} fails sleep/wakeup cycle",
        "Memory overflow in {ecu} calibration area",
        "Bus-off recovery failure on {ecu} CAN channel",
        "Diagnostic response timeout for {ecu}",
    ]

    for i in range(1, 201):
        vid = random.choice(all_vehicle_ids)
        ecu = random.choice(ECU_TYPES)
        dtc = random.choice(DTC_CODES)
        title_tmpl = random.choice(defect_titles)
        title = title_tmpl.format(ecu=ecu, dtc=dtc)
        severity = random.choices(DEFECT_SEVERITIES, weights=[10, 30, 40, 20], k=1)[0]
        status = random.choices(DEFECT_STATUSES, weights=[30, 25, 25, 20], k=1)[0]
        created = base_time + timedelta(days=random.randint(0, 160))
        updated = created + timedelta(days=random.randint(0, 20))

        cur.execute(
            "INSERT INTO defects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"DEF-{i:05d}", vid, title,
             f"Observed during integration testing. {title}. Requires investigation.",
             severity, status, ecu, dtc,
             created.isoformat(), updated.isoformat()),
        )

    conn.commit()
    conn.close()


def generate_memory_db(db_path: Path):
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE conversations (
            conversation_id TEXT PRIMARY KEY,
            messages_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE pending_actions (
            action_id TEXT PRIMARY KEY,
            tool_name TEXT NOT NULL,
            args_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            result_json TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT
        );

        CREATE TABLE memory_facts (
            fact_id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            fact_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def generate_docs():
    docs = {
        "autosar_overview.md": """# AUTOSAR Overview

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
""",
        "autosar_communication.md": """# AUTOSAR Communication Stack

## CAN Communication
The CAN (Controller Area Network) stack in AUTOSAR Classic consists of:
- **CAN Driver (CanDrv):** hardware abstraction for CAN controllers
- **CAN Interface (CanIf):** upper layer abstraction
- **CAN Transport Protocol (CanTp):** segmentation and reassembly for ISO 15765
- **PDU Router (PduR):** routes PDUs between communication stacks and COM

## SOME/IP (Adaptive)
Service-Oriented Middleware over IP:
- Service discovery via SD module
- Method calls, events, and field notifications
- Serialization of complex data types
- Used for high-bandwidth inter-ECU communication

## Communication Patterns
- **Sender-Receiver:** asynchronous signal-based (Classic)
- **Client-Server:** synchronous RPC-style (both Classic and Adaptive)
- **Publish-Subscribe:** event-driven (Adaptive SOME/IP)
""",
        "autosar_diagnostics.md": """# AUTOSAR Diagnostics (UDS/OBD)

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
""",
        "aspice_overview.md": """# Automotive SPICE (ASPICE) Overview

Automotive SPICE is a process assessment model for automotive software development, based on ISO/IEC 33000.

## Process Areas

### Primary Life Cycle Processes
- **SYS.1-5:** System Engineering (requirements, architecture, integration, testing)
- **SWE.1-6:** Software Engineering (requirements, architecture, detailed design, implementation, integration, testing)
- **ACQ/SPL:** Acquisition and Supply

### Supporting Processes
- **SUP.1:** Quality Assurance
- **SUP.8:** Configuration Management
- **SUP.9:** Problem Resolution Management
- **SUP.10:** Change Request Management

## Capability Levels
- **Level 0:** Incomplete — process not implemented
- **Level 1:** Performed — achieves its purpose
- **Level 2:** Managed — planned, monitored, and adjusted
- **Level 3:** Established — follows a defined process
- **Level 4:** Predictable — operates within defined limits
- **Level 5:** Innovating — continuously improving

## Key Artifacts
| Process | Input | Output |
|---------|-------|--------|
| SWE.1   | System requirements | Software requirements specification |
| SWE.2   | SW requirements | Software architecture document |
| SWE.3   | SW architecture | Detailed design document |
| SWE.4   | Detailed design | Source code |
| SWE.5   | Source code + SW design | Integration test report |
| SWE.6   | SW requirements | SW qualification test report |
""",
        "aspice_traceability.md": """# ASPICE Traceability and Consistency

## Bidirectional Traceability
ASPICE requires bidirectional traceability between all engineering artifacts:

```
System Requirements
    ↕
Software Requirements (SWE.1)
    ↕
Software Architecture (SWE.2)
    ↕
Detailed Design (SWE.3)
    ↕
Source Code (SWE.4)
```

Each level must trace:
- **Downward:** requirement → design element → code
- **Upward:** code → design element → requirement
- **Horizontal:** requirement → test case (verification)

## Consistency Rules
1. Every system requirement must map to at least one SW requirement
2. Every SW requirement must map to at least one architectural element
3. Every test case must trace to a requirement
4. No orphan requirements (requirements with no children)
5. No orphan code (code with no tracing to a requirement)

## Impact Analysis
When a requirement changes, traceability enables:
- Identification of all affected design elements
- Identification of all affected code modules
- Identification of all test cases that need re-execution
""",
        "asil_functional_safety.md": """# ASIL and Functional Safety (ISO 26262)

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
""",
        "asil_software_development.md": """# Safety-Related Software Development (ISO 26262 Part 6)

## Software Development Process
1. **Software Safety Requirements Specification**
   - Derived from technical safety concept
   - Each requirement tagged with ASIL
   - Safety mechanisms specified (monitoring, redundancy, plausibility checks)

2. **Software Architectural Design**
   - Modular architecture with well-defined interfaces
   - Freedom from interference between ASIL-rated and QM components
   - Error detection and handling mechanisms
   - Timing and resource constraints

3. **Software Unit Design and Implementation**
   - Coding guidelines (MISRA C/C++ for ASIL B-D)
   - Defensive programming practices
   - No dynamic memory allocation in safety-critical code
   - Fixed-point arithmetic preferred over floating-point

4. **Software Unit Testing**
   - Requirements-based testing
   - Structural coverage: statement (ASIL A), branch (ASIL B), MC/DC (ASIL C-D)
   - Boundary value analysis
   - Error guessing and fault injection

5. **Software Integration and Testing**
   - Integration strategy based on architecture
   - Interface testing between components
   - Resource usage testing (CPU, memory, stack)

## Verification Methods
- **Walk-through:** informal review
- **Inspection:** formal review with defined roles
- **Semi-formal verification:** model-based analysis
- **Formal verification:** mathematical proof (ASIL D)
""",
        "ecu_flashing.md": """# ECU Flashing and Software Update Procedures

## Flash Programming Sequence (UDS-based)
1. **Pre-conditions check**
   - Vehicle in P/N gear, engine off, stable voltage (12-14V)
   - All DTCs cleared or acknowledged

2. **Enter Programming Session**
   - DiagnosticSessionControl (0x10, sub=0x02)
   - ECU enters programming mode, disables normal communication

3. **Security Access**
   - SecurityAccess Seed (0x27, sub=0x01) → ECU returns seed
   - SecurityAccess Key (0x27, sub=0x02) → tester sends computed key
   - Failed attempts trigger lockout timer

4. **Download Sequence**
   - RequestDownload (0x34) — specify memory address and size
   - TransferData (0x36) — send data blocks with sequence counter
   - RequestTransferExit (0x37) — finalize transfer

5. **Checksum Verification**
   - RoutineControl (0x31) — trigger internal checksum calculation
   - Compare against expected checksum

6. **ECU Reset**
   - ECUReset (0x11, sub=0x01) — hard reset
   - ECU boots with new software
   - Verify new SW version via ReadDataByIdentifier

## Common Flash Failures
- **Voltage drop:** causes incomplete write → ECU may be bricked
- **CAN bus errors:** data corruption → checksum mismatch
- **Security lockout:** too many failed key attempts
- **Incompatible SW:** wrong part number/variant
- **Memory corruption:** flash wear or defective cells
""",
        "can_bus_diagnostics.md": """# CAN Bus Diagnostics and Error Handling

## CAN Error Types
- **Bit Error:** transmitter reads back different value than sent
- **Stuff Error:** more than 5 consecutive bits of same polarity
- **CRC Error:** received CRC doesn't match calculated CRC
- **Form Error:** fixed-form bit field violation (e.g., delimiter)
- **ACK Error:** no acknowledgment from any receiver

## CAN Error States
1. **Error Active:** normal operation, can send error frames
   - TEC < 128 and REC < 128
2. **Error Passive:** reduced error signaling
   - TEC ≥ 128 or REC ≥ 128
3. **Bus Off:** node disconnected from bus
   - TEC ≥ 256
   - Recovery: 128 × 11 recessive bits or power cycle

## Diagnostic Approach for CAN Issues
1. Check bus termination (120Ω at each end)
2. Verify CAN-H and CAN-L voltage levels (2.5V nominal)
3. Monitor bus load (should be < 70% sustained)
4. Check for frame drops (missing periodic messages)
5. Analyze error frame frequency and distribution
6. Check for electromagnetic interference sources

## AUTOSAR CAN Error Handling
- **CanSM (CAN State Manager):** manages bus state transitions
- **ComM (Communication Manager):** handles communication modes
- Bus-off recovery: automatic or on-request, configurable delay
""",
        "integration_testing.md": """# Automotive Software Integration Testing

## Integration Test Levels
1. **Software Unit Integration Test (SWE.5)**
   - Tests interactions between software units within a component
   - Focus: internal interfaces, data flow, control flow
   - Tools: unit test frameworks with mock/stub support

2. **Software Integration Test**
   - Tests interactions between software components
   - Focus: inter-component communication, resource sharing
   - Environment: SIL (Software-in-the-Loop) or HIL (Hardware-in-the-Loop)

3. **System Integration Test (SYS.4)**
   - Tests interactions between ECUs in the vehicle network
   - Focus: CAN/LIN/Ethernet communication, timing, diagnostics
   - Environment: integration bench or vehicle

## Test Types
- **Communication tests:** message routing, signal mapping, timing
- **Diagnostic tests:** UDS service handling, DTC storage/clearing
- **Flash tests:** SW update procedure, rollback, recovery
- **Sleep/wakeup tests:** network management, partial networking
- **Gateway tests:** routing between different bus systems
- **OTA tests:** over-the-air update procedure end-to-end

## Test Verdicts
- **Pass:** all assertions met, no unexpected DTCs
- **Fail:** assertion violated or unexpected behavior
- **Blocked:** pre-condition not met, environment issue
- **Skipped:** intentionally not executed (known limitation)

## Key Metrics
- Pass rate: target > 95% for release gate
- Defect detection rate by test type
- Test execution time (regression suite < 4 hours)
- Coverage: requirement coverage > 98%
""",
        "vehicle_network_architecture.md": """# Vehicle Network Architecture

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
""",
        "ota_updates.md": """# Over-the-Air (OTA) Software Updates

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
""",
        "defect_management.md": """# Defect Management in Automotive Software

## Defect Lifecycle
```
New → Open → In Progress → Resolved → Closed
                ↓                ↓
            Deferred          Reopened
```

## Severity Levels
- **Critical:** system crash, safety function failure, no workaround
- **Major:** feature not working, workaround exists
- **Minor:** cosmetic issue, non-critical feature degradation
- **Trivial:** typo, minor UI issue, documentation error

## Priority vs. Severity
| Priority | When to fix |
|----------|-------------|
| P1       | Immediate (blocks release) |
| P2       | Current sprint |
| P3       | Next sprint |
| P4       | Backlog |

## Defect Report Content
1. **Summary:** one-line description
2. **Description:** steps to reproduce, expected vs. actual behavior
3. **Environment:** vehicle, ECU, SW version, test bench
4. **Severity and Priority**
5. **Attachments:** logs, traces, screenshots
6. **Root cause analysis:** (filled during investigation)
7. **Fix description:** (filled during resolution)

## Metrics
- Open defect count by severity and age
- Mean time to resolution (MTTR)
- Defect injection rate (new defects per week)
- Escape rate (defects found after release)
""",
        "software_versioning.md": """# Software Versioning in Automotive

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
""",
        "process_improvement.md": """# Continuous Process Improvement in Automotive SW

## Improvement Frameworks
### PDCA (Plan-Do-Check-Act)
1. Plan: identify improvement opportunity
2. Do: implement change on small scale
3. Check: measure results against goals
4. Act: standardize or adjust

### Lessons Learned
After each release/milestone:
- What went well?
- What didn't go well?
- What should we change?
- Document and share across teams

## Key Process Indicators (KPIs)
- **Build success rate:** target > 98%
- **Test automation rate:** target > 80%
- **Defect escape rate:** target < 2%
- **Mean time to integrate:** time from code commit to integration test pass
- **Rework rate:** percentage of work items requiring rework
- **First pass yield:** percentage of integration tests passing on first run

## Tool Chain Integration
- Requirements management (DOORS, Polarion)
- Version control (Git, SVN)
- CI/CD (Jenkins, GitLab CI)
- Test management (TestRail, qTest)
- Defect tracking (Jira, Mantis)
- Configuration management (baseline tools)

## Process Audit
- Internal audits: quarterly
- Supplier assessments: ASPICE-based
- Customer audits: project-specific
- Certification audits: ISO 26262, IATF 16949
""",
    }

    DOCS_DIR.mkdir(exist_ok=True)
    for filename, content in docs.items():
        (DOCS_DIR / filename).write_text(content.strip() + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    DATA_DIR.mkdir(exist_ok=True)

    print("Generating PDM vehicle data...")
    vehicles = generate_pdm_vehicles(10)
    pdm_path = DATA_DIR / "pdm_vehicles.json"
    pdm_path.write_text(json.dumps(vehicles, indent=2))
    print(f"  → {pdm_path} ({len(vehicles)} vehicles)")

    print("Generating integration logs...")
    logs = generate_integration_logs(vehicles, 200)
    logs_path = DATA_DIR / "integration_logs.jsonl"
    with open(logs_path, "w") as f:
        for entry in logs:
            f.write(json.dumps(entry) + "\n")
    print(f"  → {logs_path} ({len(logs)} entries)")

    print("Generating fleet database...")
    fleet_db_path = DATA_DIR / "fleet.db"
    generate_fleet_db(vehicles, fleet_db_path)
    print(f"  → {fleet_db_path}")

    print("Generating memory database...")
    memory_db_path = DATA_DIR / "memory.db"
    generate_memory_db(memory_db_path)
    print(f"  → {memory_db_path}")

    print("Generating RAG documents...")
    generate_docs()
    doc_count = len(list(DOCS_DIR.glob("*.md")))
    print(f"  → {DOCS_DIR}/ ({doc_count} documents)")

    print("\nDone! All synthetic data generated.")


if __name__ == "__main__":
    main()
