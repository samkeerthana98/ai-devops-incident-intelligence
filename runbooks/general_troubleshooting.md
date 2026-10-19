# Runbook: General Service Troubleshooting

## Overview

This runbook provides a general-purpose checklist for diagnosing and recovering
from service issues that do not match a specific incident pattern. Use this when
the symptoms are unclear or span multiple categories.

## Common Causes

1. **Service not responding** — The process crashed, is hung, or failed to start.
2. **Connectivity issues** — Network configuration, firewall rules, or DNS
   problems prevent components from communicating.
3. **Configuration drift** — Environment-specific settings differ from expected
   values, causing unexpected behavior.
4. **Authentication or authorisation failure** — Expired tokens, rotated secrets,
   or misconfigured permissions block legitimate requests.
5. **Data inconsistency** — Corrupted, missing, or stale data causes unexpected
   application behavior.

## Diagnostic Steps

1. Verify the service is running: check process list, container status, or
   health endpoint.
2. Check recent logs for errors, warnings, or unusual patterns.
3. Verify network connectivity between the service and its dependencies.
4. Compare current configuration against the expected baseline.
5. Test authentication and authorisation paths.
6. Check for recent deployments, config changes, or infrastructure events.

## Recovery Actions

- Restart the affected service or container.
- Restore the last known good configuration.
- Re-create or rotate expired credentials and tokens.
- Re-sync data from the authoritative source if inconsistency is detected.
- Failover to a healthy replica or standby instance.
- Roll back the most recent change if it introduced the issue.

## Prevention

- Maintain up-to-date documentation of service dependencies and configuration.
- Use infrastructure-as-code to prevent configuration drift.
- Monitor health endpoints and alert on service unavailability.
- Implement automated backups and periodic data integrity checks.
- Schedule regular disaster recovery drills.
