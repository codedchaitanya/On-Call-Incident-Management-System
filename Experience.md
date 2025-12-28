# Reflection: On-Call Incident Management System

## Understanding the Problem

This assignment tested my ability to build a **scoped, correct system** rather than a feature-rich one. The implicit requirement was to demonstrate:
1. **Clear thinking** about domain logic (on-call scheduling, incident state machines)
2. **Edge-case handling** (what happens when no one is on-call? When schedules overlap?)
3. **Trade-off reasoning** (why mocked alerts? Why simple deduplication instead of distributed consensus?)
4. **Code organization** (how to separate concerns so logic is testable and changeable)

I interpreted this as: *Build a system that could scale to real incidents if needed, but today just demonstrate that the core mechanics are correct.*

---

## Design Decisions

### Why Django REST Framework?

Django + DRF minimized boilerplate while keeping me focused on business logic. The admin portal came free, which was useful for managing schedules. The serializer layer provided a clean boundary between domain objects and API contracts.

Alternative (FastAPI) would have been faster to write but less forgiving on edge cases—Django's ORM encouraged me to think through constraints explicitly (e.g., `auto_now_add=True` preventing manual time overrides during testing).

### Why Backend-Heavy Logic?

All business logic lives in the service layer (`OnCallService`, `IncidentService`), not in views or JavaScript. This decision reflected real-world constraints:
- **Incidents are safety-critical**: I wouldn't trust client-side state validation
- **Auditability**: Server-side logic is easier to trace when things go wrong
- **Consistency**: If two users trigger simultaneously, the backend enforces rules, not the UI

The frontend is intentionally dumb—it polls and displays, nothing more.

### Why Console Alerts?

Mocking alerts with `print()` statements was a pragmatic choice:
1. **Removed external dependency** (no need to authenticate with Slack/PagerDuty)
2. **Equivalent to real alerting** in function (just a side effect that happens when an incident is created)
3. **Easy to extend** (replace `print()` with `requests.post()` to Slack in 2 minutes)

The real value wasn't in the delivery mechanism—it was in proving the system *calls* alerts at the right moment.

---

## Challenges Faced

### Time-Based Logic

Escalation required reasoning about time correctly. The challenge: incidents created at different microsecond-boundaries could behave differently if I used `<` vs `<=`. I solved this by:
- Using `timezone.now()` consistently everywhere (no client time)
- Testing with manual time manipulation (creating incidents with `created_at=now - 10 minutes`)
- Documenting the timeout window clearly (5 minutes) rather than guessing

### State Transitions

Incident state machines are easy to get wrong. TRIGGERED → RESOLVED should never be allowed directly, but I almost allowed it as a shortcut. Instead, I:
- Mapped all valid transitions explicitly in tests
- Threw `ValueError` for invalid ones
- Made the model enforce this at the service layer, not just in the view

This caught bugs later when I refactored escalation logic.

### Deduplication

Early versions checked `title == title` across all services, which was too greedy (same error in two different services should be separate incidents). I fixed this to query `service_name + title + time_window`, which matched real-world behavior.

### Escalation Without User Reassignment

Initially, I designed escalation to assign incidents to escalation-level users. This created state explosion:
- What if no escalation user was configured?
- What if the escalation user was on vacation?
- How do you know if the escalation was "handled" or just reassigned?

I simplified: escalation now just flags the incident as "too old, needs human attention" without changing assignment. Operators can manually reassign if needed. This was more extensible.

---

## Trade-offs Made

| Choice | Benefit | Cost |
|--------|---------|------|
| SQLite + simple polling | Fast to implement, clear to test | Doesn't scale beyond one server |
| Console alerts | No external dependencies | No real integration |
| 5-minute timeout | Simple to reason about | Hard-coded (should be configurable) |
| No audit logs | Fewer tables to manage | Can't trace why incidents state changed |
| No incident comments | Simpler model | Real systems need context |

These weren't oversights—they were conscious decisions to stay focused on demonstrating core mechanics rather than completeness.

---

## Key Learnings

### This System Demonstrates

1. **Correctness over speed**: All 19 tests pass, including edge cases. I'd rather have fewer features that work than more that don't.
2. **Time-based logic is hard**: Building a simple escalation timeout taught me that time-based systems require careful testing and clear intent.
3. **State machines need safeguards**: One test caught an invalid transition I almost shipped. Explicit state validation in the service layer pays off.
4. **APIs should be dumb**: Making views and JavaScript thin forced me to think clearly about where responsibility lives.

### Reflections on Real Systems

Real incident systems (PagerDuty, Opsgenie) solve harder problems:
- **Distributed**: Multiple regions, eventual consistency
- **Stateful**: On-call rotations, escalation policies, notification rules
- **Integrated**: Webhooks, APIs, custom logic
- **Observable**: Audit trails, dashboards, SLA tracking

But they all start here: *who is on-call, route alerts to them, escalate if they don't respond.* Getting this foundation right—with clear thinking and test coverage—is the hard part. The rest is engineering.

---

## Conclusion

This assignment was less about "build the most features" and more about "show how you think about trade-offs, edge cases, and correctness." I tried to reflect that in every design decision: choosing Django for admin automation, putting logic in services instead of views, mocking alerts to stay focused, and writing tests to catch the mistakes I'd make.

If I were to extend this, I'd add Celery for reliability, PostgreSQL for persistence, and real Slack integration—but only once the core mechanics prove they work.
