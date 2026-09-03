# Defect Management in Automotive Software

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
