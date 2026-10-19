# Runbook: High Latency

## Overview

High latency means the application is responding to requests more slowly than the
expected or acceptable threshold. This degrades user experience and can lead to
timeouts, cascading failures, and customer dissatisfaction.

## Common Causes

1. **Slow database queries** — Missing indexes, large table scans, or unoptimised
   queries add seconds to response time.
2. **Resource contention** — High CPU or memory usage on the server causes request
   queuing and slow processing.
3. **Network bottlenecks** — Slow network paths between the application and
   databases, caches, or external APIs.
4. **Lock contention** — Database locks, thread locks, or mutex contention
   serialize requests that should run concurrently.
5. **Inefficient application code** — N+1 query patterns, synchronous calls to
   slow external services, or heavy in-memory processing.
6. **Insufficient capacity** — The server or container does not have enough CPU,
   memory, or connections to handle the current load.

## Diagnostic Steps

1. Identify the slow endpoint or service using APM traces or access-log timing.
2. Check database query performance — look for queries taking more than 500 ms.
3. Monitor system metrics: CPU, memory, network I/O, and disk latency.
4. Review application-level metrics: thread pool usage, connection pool wait times.
5. Check for recent traffic spikes or changes in request patterns.
6. Examine external dependency response times.

## Recovery Actions

- Scale out by adding more application instances or containers.
- Restart the slow instance to clear potential memory leaks or stuck threads.
- Enable caching for frequently accessed, slow-changing data.
- Temporarily throttle or rate-limit non-critical traffic.
- Optimise the identified slow query by adding indexes or rewriting it.
- Increase database connection pool size if pool exhaustion is detected.

## Prevention

- Set latency SLOs and alert when p99 exceeds the threshold.
- Add database indexes for columns used in common query filters and joins.
- Implement caching at appropriate layers (application, database, CDN).
- Load test regularly to understand capacity limits.
- Monitor dependency latency and add timeouts and circuit breakers.
