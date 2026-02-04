# GOAL

The `datadog-sync-cli` is missing endpoints available in the [Datadog API](https://docs.datadoghq.com/api/latest/?tab=python). The goals of this project are to:

* Inventory all available inputs in the `datadog-sync-cli`
* Inventory all available resources in the Datadog API
* Bridge the gap between the two tools, with a goal of 100% parity where appropriate. "Appropriate" in this context means: If a user wants to migrate assets from one Datadog account to another, they should be able to migrate any resource that can be retrieved through the API. "Resource" in this context is an artifact that lives in a Datadog account, but is *not* telemetry such as logs, metrics, traces, RUM events, security signals, etc. 

# PRACTICES

* ALWAYS follow the practices found in @PYTHON.md
* ALWAYS use `uv` to handle virtual envrionments. ALWAYS use a virtual environment.
* NEVER use emoji
* Use the @code-simplifier plugin to review and improve the codebase prior to committing. Always create a markdown file called code-simplification-<timestamp>.md and include a detailed analysis of the changes you've made and why those changes will simplify the code. Be as detailed as possible. Write your analysis as if you were training a team of junior engineers on good Python coding practices.

