# Datadog API Inventory

This document provides a comprehensive inventory of Datadog API resources, comparing what is currently implemented in `datadog-sync-cli` against the full Datadog API surface.

## Overview

- **Implemented Resources**: 48 (40 original + 8 newly added)
- **Missing Resources**: 21+ (organized by priority)
- **Excluded Resources**: 9 (telemetry/runtime data)

---

## Implemented Resources (48 Total)

The following resources are currently supported by `datadog-sync-cli` for migration between Datadog organizations.

### Monitoring

| Resource | API Path | Description |
|----------|----------|-------------|
| `monitors` | `/api/v1/monitor` | Alerting monitors with query-based conditions |
| `downtimes` | `/api/v1/downtime` | Scheduled downtimes (v1 API, legacy) |
| `downtime_schedules` | `/api/v2/downtime` | Scheduled downtimes (v2 API) |
| `security_monitoring_rules` | `/api/v2/security_monitoring/rules` | SIEM detection rules |
| `slo_corrections` | `/api/v1/slo/correction` | SLO status corrections |

### Dashboards and Visualization

| Resource | API Path | Description |
|----------|----------|-------------|
| `dashboards` | `/api/v1/dashboard` | Dashboard configurations |
| `dashboard_lists` | `/api/v1/dashboard/lists/manual` | Manual dashboard organization lists |
| `powerpacks` | `/api/v2/powerpacks` | Reusable dashboard widget packs |
| `notebooks` | `/api/v1/notebooks` | Investigative notebooks |

### Logs Management

| Resource | API Path | Description |
|----------|----------|-------------|
| `logs_pipelines` | `/api/v1/logs/config/pipelines` | Log processing pipelines (including integration pipelines) |
| `logs_pipelines_order` | `/api/v1/logs/config/pipeline-order` | Pipeline processing order |
| `logs_custom_pipelines` | `/api/v1/logs/config/pipelines` | Custom log pipelines (excludes read-only integration pipelines) |
| `logs_indexes` | `/api/v1/logs/config/indexes` | Log index configurations |
| `logs_indexes_order` | `/api/v1/logs/config/index-order` | Index routing order |
| `logs_archives` | `/api/v2/logs/config/archives` | Log archive destinations |
| `logs_archives_order` | `/api/v2/logs/config/archive-order` | Archive routing order |
| `logs_metrics` | `/api/v2/logs/config/metrics` | Log-based custom metrics |

### Users and Access Control

| Resource | API Path | Description |
|----------|----------|-------------|
| `users` | `/api/v2/users` | User accounts |
| `roles` | `/api/v2/roles` | RBAC roles with permissions |
| `teams` | `/api/v2/team` | Team management |
| `team_memberships` | `/api/v2/team/{id}/memberships` | Team member associations |
| `authn_mappings` | `/api/v2/authn_mappings` | SAML/IdP attribute mappings to roles/teams |
| `restriction_policies` | `/api/v2/restriction_policy` | Resource access policies |
| `logs_restriction_queries` | `/api/v2/logs/config/restriction_queries` | Log access restrictions by role |

### Data Security

| Resource | API Path | Description |
|----------|----------|-------------|
| `sensitive_data_scanner_groups` | `/api/v2/sensitive-data-scanner/config` | SDS scanning groups |
| `sensitive_data_scanner_rules` | `/api/v2/sensitive-data-scanner/config` | SDS scanning rules |
| `sensitive_data_scanner_groups_order` | `/api/v2/sensitive-data-scanner/config` | SDS group ordering |

### Synthetic Monitoring

| Resource | API Path | Description |
|----------|----------|-------------|
| `synthetics_tests` | `/api/v1/synthetics/tests` | API, browser, and mobile synthetic tests |
| `synthetics_private_locations` | `/api/v1/synthetics/private-locations` | Private test execution locations |
| `synthetics_global_variables` | `/api/v1/synthetics/variables` | Global variables for synthetic tests |
| `synthetics_mobile_applications` | `/api/unstable/synthetics/mobile/applications` | Mobile application configurations |
| `synthetics_mobile_applications_versions` | `/api/unstable/synthetics/mobile/applications/versions` | Mobile application versions |

### Service Level Objectives

| Resource | API Path | Description |
|----------|----------|-------------|
| `service_level_objectives` | `/api/v1/slo` | SLO definitions |

### Metrics

| Resource | API Path | Description |
|----------|----------|-------------|
| `metrics_metadata` | `/api/v1/metrics` | Metric metadata (units, descriptions) |
| `metric_tag_configurations` | `/api/v2/metrics` | Metric tag configurations |
| `metric_percentiles` | `/metric/distribution/summary_aggr` | Distribution metric percentiles |

### APM and RUM

| Resource | API Path | Description |
|----------|----------|-------------|
| `rum_applications` | `/api/v2/rum/applications` | RUM application configurations |
| `spans_metrics` | `/api/v2/apm/config/metrics` | Span-based custom metrics |

### Infrastructure

| Resource | API Path | Description |
|----------|----------|-------------|
| `host_tags` | `/api/v1/tags/hosts` | Host tag assignments |

### Cloud Integrations (NEW)

| Resource | API Path | Description |
|----------|----------|-------------|
| `aws_integration` | `/api/v1/integration/aws` | AWS account integration |
| `gcp_integration` | `/api/v2/integration/gcp/accounts` | Google Cloud Platform integration |
| `azure_integration` | `/api/v1/integration/azure` | Azure subscription integration |
| `fastly_integration` | `/api/v2/integrations/fastly/accounts` | Fastly CDN integration |
| `webhooks_integration` | `/api/v1/integration/webhooks/configuration/webhooks` | Custom webhook integrations |
| `pagerduty_integration` | `/api/v1/integration/pagerduty/configuration/services` | PagerDuty alerting integration |
| `slack_integration_channels` | `/api/v1/integration/slack/configuration/accounts` | Slack notification channels |

### Service Management (NEW)

| Resource | API Path | Description |
|----------|----------|-------------|
| `service_definition` | `/api/v2/services/definitions` | Service definitions and ownership |

---

## Missing Resources

The following resources are available in the Datadog API but not yet implemented in `datadog-sync-cli`.

### Cloud Integrations (Remaining)

| Resource | API Path | Description |
|----------|----------|-------------|
| AWS Logs Integration | `/api/v2/integration/aws/logs` | AWS CloudWatch logs forwarding |
| Cloudflare Integration | `/api/v2/integrations/cloudflare` | Cloudflare account integration |
| Confluent Cloud | `/api/v2/integrations/confluent-cloud` | Confluent Cloud integration |
| OCI Integration | `/api/v2/integrations/oci` | Oracle Cloud Infrastructure integration |
| Okta Integration | `/api/v2/integrations/okta` | Okta identity provider integration |
| Jira Integration | `/api/v2/integration/jira` | Jira issue tracking integration |
| Microsoft Teams Integration | `/api/v2/integration/ms-teams` | Microsoft Teams notification integration |

### Service Management

| Resource | API Path | Description |
|----------|----------|-------------|
| Service Scorecards | `/api/v2/scorecard` | Service health scorecards |
| Incidents | `/api/v2/incidents` | Incident management (templates and settings) |
| Case Management | `/api/v2/cases` | Case management configuration |

### Observability Infrastructure

| Resource | API Path | Description |
|----------|----------|-------------|
| Observability Pipelines | `/api/v2/observability_pipelines` | Data pipeline configurations |
| Logs Custom Destinations | `/api/v2/logs/config/custom-destinations` | Custom log forwarding destinations |
| APM Retention Filters | `/api/v2/apm/config/retention-filters` | Trace retention filter rules |

### Platform and Automation

| Resource | API Path | Description |
|----------|----------|-------------|
| App Builder | `/api/v2/app-builder` | Custom application definitions |
| Workflow Automation | `/api/v2/workflows` | Automated workflow definitions |
| Action Connections | `/api/v2/actions/connections` | External service connections for workflows |

### Security

| Resource | API Path | Description |
|----------|----------|-------------|
| Cloud Workload Security | `/api/v2/security_monitoring/cloud_workload_security` | CWS custom rules |
| Application Security | `/api/v2/application_security` | ASM custom rules |

### Organization and Access

| Resource | API Path | Description |
|----------|----------|-------------|
| Domain Allowlist | `/api/v2/domain_allowlist` | Allowed email domains for login |
| IP Allowlist | `/api/v2/ip_allowlist` | IP-based access restrictions |
| Organizations | `/api/v1/org` | Organization settings |

---

## Prioritization

### Tier 1 - High Priority (Cloud Integrations)

Remaining integrations critical for account migration:

1. Cloudflare Integration
2. OCI Integration
3. Okta Integration
4. Jira Integration
5. Microsoft Teams Integration
6. Confluent Cloud
7. AWS Logs Integration

**Status**: 7 of 14 cloud integrations implemented (AWS, GCP, Azure, Fastly, Webhooks, PagerDuty, Slack)

### Tier 2 - Medium Priority (Service/DevOps Configuration)

Important for complete platform migration:

1. Service Scorecards
2. Observability Pipelines
3. Logs Custom Destinations
4. APM Retention Filters
5. Workflow Automation
6. App Builder
7. Incidents (configuration templates)
8. Case Management

**Status**: 1 of 9 implemented (Service Definition)

### Tier 3 - Lower Priority (Security Rules)

Organization-specific security rules:

1. Cloud Workload Security (custom rules)
2. Application Security (custom rules)

**Status**: 0 of 2 implemented

---

## Excluded Resources (Not Migratable)

The following API resources are intentionally excluded because they represent telemetry data, computed values, or runtime state rather than configuration.

| Resource | API Path | Reason |
|----------|----------|--------|
| DORA Metrics | `/api/v2/dora` | Telemetry events, not configuration |
| CI Visibility Pipelines | `/api/v2/ci/pipelines` | Telemetry data |
| CI Visibility Tests | `/api/v2/ci/tests` | Telemetry data |
| Containers | `/api/v2/containers` | Runtime discovery data |
| Container Images | `/api/v2/container_images` | Runtime discovery data |
| Hosts | `/api/v1/hosts` | Runtime discovery data |
| Entity Risk Scores | `/api/v2/entity_risk_scores` | Computed values |
| Audit Logs | `/api/v2/audit` | Read-only historical data |
| Cloud Cost Management | `/api/v2/cost` | Billing data |
| Data Deletion | `/api/v2/deletion` | Destructive operation, not migration |
| Snapshots | `/api/v1/graph/snapshot` | Point-in-time graph images |

---

## Implementation Notes

### Adding New Resources

To add support for a new resource:

1. Create a new file in `datadog_sync/model/`
2. Inherit from `BaseResource`
3. Define `resource_type` and `resource_config` (ResourceConfig dataclass)
4. Implement required abstract methods:
   - `get_resources()` - Fetch from source organization
   - `import_resource()` - Store locally
   - `create_resource()` - Create at destination
   - `update_resource()` - Update at destination
   - `delete_resource()` - Delete at destination
   - `pre_resource_action_hook()` - Pre-processing
   - `pre_apply_hook()` - Pre-apply validation

### Key ResourceConfig Fields

- `base_path`: API endpoint path (e.g., `/api/v1/monitor`)
- `resource_connections`: Dict mapping dependent resource types to attribute paths for ID remapping
- `excluded_attributes`: Fields to ignore during sync/diff (dot notation)
- `concurrent`: Whether resource can be synced in parallel (default True)
- `tagging_config`: Optional TaggingConfig for adding default tags

### Testing

- Unit tests in `tests/unit/`
- Integration tests require `DD_SOURCE_*` and `DD_DESTINATION_*` environment variables
- Run with `pytest -v tests/unit/test_<resource>.py`

---

## References

- [Datadog API Documentation](https://docs.datadoghq.com/api/latest/)
- [datadog-sync-cli Repository](https://github.com/DataDog/datadog-sync-cli)

---

*Last updated: 2026-02-04*
