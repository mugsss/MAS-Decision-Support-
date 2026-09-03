# Safety-Related Software Development (ISO 26262 Part 6)

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
