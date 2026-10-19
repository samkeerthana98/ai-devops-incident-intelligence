# Runbook: HTTP 500 Internal Server Error

## Overview

An HTTP 500 status code indicates the server encountered an unexpected condition
that prevented it from fulfilling the request. This is typically a server-side
application error rather than a client issue.

## Common Causes

1. **Uncaught application exception** — A bug in application code causes an unhandled
   exception (e.g., null reference, type error).
2. **Database connection failure** — The application cannot reach the database or
   the query times out.
3. **Resource exhaustion** — The server runs out of memory, file descriptors, or
   thread pool capacity.
4. **Configuration error** — Incorrect environment variables, missing config files,
   or bad secrets cause startup or runtime failures.
5. **Dependency service failure** — A downstream service (payment gateway, cache,
   message queue) returns an error that is not handled gracefully.

## Diagnostic Steps

1. Check application logs for the stack trace associated with the 500 response.
2. Verify database connectivity and query performance.
3. Check system resources: CPU, memory, disk space, open file descriptors.
4. Review recent deployments or configuration changes.
5. Verify downstream service health and connectivity.

## Recovery Actions

- Restart the affected application instance or container.
- Roll back the most recent deployment if the errors started after a release.
- Increase resource limits if exhaustion is confirmed.
- Add proper error handling and retry logic for downstream service calls.
- Temporarily enable a circuit breaker or degraded-mode response for affected endpoints.

## Prevention

- Implement comprehensive error handling and logging around all external calls.
- Use health checks and readiness probes to catch failures early.
- Run integration tests that cover failure scenarios.
- Monitor error rates and set up alerts for sudden spikes in 500 responses.
