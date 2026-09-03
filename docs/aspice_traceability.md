# ASPICE Traceability and Consistency

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
