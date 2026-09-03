# AUTOSAR Communication Stack

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
