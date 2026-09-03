# ECU Flashing and Software Update Procedures

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
