# Plan: Datadog API Parity Inventory

## Objective

Create a comprehensive inventory comparing `datadog-sync-cli` resources against the Datadog API, then bridge the gap to achieve 100% parity for migratable resources.

---

## Phase 1: Inventory (Current State)

### CLI Resources Implemented (40 total)

| Category | Resources |
|----------|-----------|
| Monitoring | monitors, downtimes, downtime_schedules, security_monitoring_rules, slo_corrections |
| Dashboards | dashboards, dashboard_lists, powerpacks |
| Logs | logs_pipelines, logs_pipelines_order, logs_custom_pipelines, logs_indexes, logs_indexes_order, logs_archives, logs_archives_order, logs_metrics |
| Users/Access | users, roles, teams, team_memberships, authn_mappings, restriction_policies, logs_restriction_queries |
| Data Security | sensitive_data_scanner_groups, sensitive_data_scanner_rules, sensitive_data_scanner_groups_order |
| Synthetics | synthetics_tests, synthetics_private_locations, synthetics_global_variables, synthetics_mobile_applications, synthetics_mobile_applications_versions |
| SLOs | service_level_objectives |
| Notebooks | notebooks |
| Metrics | metrics_metadata, metric_tag_configurations, metric_percentiles |
| APM/RUM | rum_applications, spans_metrics |
| Infrastructure | host_tags |

### Missing from CLI (Gap Analysis)

#### Cloud Integrations (HIGH PRIORITY)

- **AWS Integration** - `/api/v2/integration/aws/accounts`
- **AWS Logs Integration** - `/api/v2/integration/aws/logs`
- **Azure Integration** - `/api/v1/integration/azure`
- **GCP Integration** - `/api/v2/integration/gcp/accounts`
- **Cloudflare Integration** - `/api/v2/integrations/cloudflare`
- **Confluent Cloud** - `/api/v2/integrations/confluent-cloud`
- **Fastly Integration** - `/api/v2/integrations/fastly`
- **OCI Integration** - `/api/v2/integrations/oci`
- **Okta Integration** - `/api/v2/integrations/okta`
- **PagerDuty Integration** - `/api/v1/integration/pagerduty`
- **Slack Integration** - `/api/v1/integration/slack`
- **Jira Integration** - `/api/v2/integration/jira`
- **Microsoft Teams Integration** - `/api/v2/integration/ms-teams`
- **Webhooks Integration** - `/api/v1/integration/webhooks`

#### Service Management

- **Incidents** - `/api/v2/incidents`
- **Incident Services** - `/api/v2/services` (deprecated, use Teams)
- **Incident Teams** - (deprecated, use Teams API)
- **Case Management** - `/api/v2/cases`
- **Service Catalog** - `/api/v2/services/definitions`
- **Service Definition** - `/api/v2/services/definitions`
- **Service Dependencies** - `/api/v2/service/dependencies`
- **Service Scorecards** - `/api/v2/scorecard`

#### Software Delivery / DevOps

- **DORA Metrics** - `/api/v2/dora` (events, not config - may be telemetry)
- **CI Visibility Pipelines** - `/api/v2/ci/pipelines`
- **CI Visibility Tests** - `/api/v2/ci/tests`
- **Deployment Gates** - `/api/v2/deployment_gates`

#### Security

- **Cloud Workload Security** - `/api/v2/security_monitoring/cloud_workload_security`
- **CSM Agents** - `/api/v2/csm/agents`
- **CSM Threats** - `/api/v2/security/threats`
- **CSM Coverage Analysis** - `/api/v2/csm/coverage`
- **Application Security** - `/api/v2/application_security`
- **Agentless Scanning** - `/api/v2/agentless_scanning`
- **Entity Risk Scores** - `/api/v2/entity_risk_scores` (may be computed, not config)

#### Infrastructure

- **Hosts** - `/api/v1/hosts` (list/mute, not config migration)
- **Containers** - `/api/v2/containers` (runtime data, not config)
- **Container Images** - `/api/v2/container_images` (runtime data)
- **Fleet Automation** - `/api/v2/fleet`
- **Network Device Monitoring** - `/api/v2/network_device`
- **Cloud Network Monitoring** - `/api/v2/network/cloud`

#### Observability Infrastructure

- **Observability Pipelines** - `/api/v2/observability_pipelines`
- **Logs Custom Destinations** - `/api/v2/logs/config/custom-destinations`
- **APM Retention Filters** - `/api/v2/apm/config/retention-filters`

#### Platform / Automation

- **App Builder** - `/api/v2/app-builder`
- **Action Connections** - `/api/v2/actions/connections`
- **Actions Datastores** - `/api/v2/actions/datastores`
- **Datasets** - `/api/v2/datasets`
- **Workflow Automation** - `/api/v2/workflows`
- **API Management** - `/api/v2/apicatalog`

#### Organization / Access

- **Domain Allowlist** - `/api/v2/domain_allowlist`
- **IP Allowlist** - `/api/v2/ip_allowlist`
- **Organizations** - `/api/v1/org` (create/update org settings)
- **Audit** - `/api/v2/audit` (logs, likely read-only)

#### Other

- **Error Tracking** - `/api/v2/error-tracking`
- **Cloud Cost Management** - `/api/v2/cost` (likely billing, excluded)
- **Data Deletion** - `/api/v2/deletion` (destructive, not migration)
- **Snapshots** - `/api/v1/graph/snapshot` (point-in-time, not config)

---

## Phase 2: Prioritization

### Tier 1 - High Priority (Cloud Integrations)

These are explicitly mentioned as missing and critical for account migration:

1. AWS Integration
2. GCP Integration
3. Azure Integration
4. Cloudflare Integration
5. Fastly Integration
6. OCI Integration
7. Okta Integration
8. PagerDuty Integration
9. Slack Integration
10. Jira Integration
11. Microsoft Teams Integration
12. Webhooks Integration
13. Confluent Cloud

### Tier 2 - Medium Priority (Service/DevOps Config)

Important for complete platform migration:

1. Service Catalog / Service Definition
2. Service Scorecards
3. Observability Pipelines
4. Logs Custom Destinations
5. APM Retention Filters
6. Workflow Automation
7. App Builder
8. Incidents (if configurable templates exist)
9. Case Management

### Tier 3 - Lower Priority (Security Rules)

May have org-specific rules worth migrating:

1. Cloud Workload Security (custom rules)
2. Application Security (custom rules)
3. CSM Threats (custom rules)

### Excluded (Not Migratable)

- DORA Metrics (telemetry events)
- CI Visibility data (telemetry)
- Containers/Container Images (runtime data)
- Hosts (runtime data)
- Entity Risk Scores (computed)
- Audit logs (read-only)
- Cloud Cost Management (billing)
- Data Deletion (destructive operation)
- Snapshots (point-in-time graphs)

---

## Phase 3: Implementation Approach

### For Each New Resource

1. Create new file in `datadog_sync/model/`
2. Inherit from `BaseResource`
3. Define `resource_type` and `resource_config`
4. Implement required methods:
   - `get_resources()` - fetch from source
   - `import_resource()` - store locally
   - `create_resource()` - create at destination
   - `update_resource()` - update at destination
   - `delete_resource()` - delete at destination
   - `pre_resource_action_hook()` - pre-processing
   - `pre_apply_hook()` - pre-apply validation

### Testing Strategy

- Unit tests in `tests/unit/`
- Integration tests requiring `DD_SOURCE_*` and `DD_DESTINATION_*` env vars
- Follow existing test patterns

---

## Immediate Next Steps

1. **Create inventory document** - Formalize the above as `docs/api-inventory.md` in the repo
2. **Validate API endpoints** - Confirm each missing resource's exact API paths and capabilities before implementation
3. **Identify simplest integration** - Analyze API complexity to pick the easiest first implementation
4. **Implement first resource** - Create proof-of-concept with full test coverage
5. **Create implementation template** - Document the pattern for adding new resources

---

## Critical Files

- `datadog_sync/model/` - All resource implementations
- `datadog_sync/utils/base_resource.py` - Base class to inherit
- `datadog_sync/utils/resource_utils.py` - Resource utilities
- `datadog_sync/utils/custom_client.py` - HTTP client for API calls
- `tests/unit/` - Unit test directory

---

## Verification

After implementing each resource:

1. Run `pytest -v tests/unit/test_<resource>.py`
2. Run `tox -e ruff` and `tox -e black`
3. Test import: `datadog-sync import --resources <resource>`
4. Test sync: `datadog-sync sync --resources <resource>`
5. Test diffs: `datadog-sync diffs --resources <resource>`
