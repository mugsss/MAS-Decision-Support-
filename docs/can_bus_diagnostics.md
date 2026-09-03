# CAN Bus Diagnostics and Error Handling

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
