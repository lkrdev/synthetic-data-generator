---
name: data-designer
description: Master synthetic data generation skill. Use when creating synthetic datasets, designing schemas, generating parquet data, or exporting tables to BigQuery.
argument-hint: [describe the dataset you want to generate and target destination]
license: Apache-2.0
metadata:
  owner: lkr.dev
---

# DataDesigner: Master Autonomous Data Generation Skill

Use this skill when you need to build, sample, test, or generate synthetic datasets.

## Zero-Install Execution Model

DataDesigner is available as an MCP server running directly via `uvx`:
```bash
uvx --from git+https://github.com/lkrdev/synthetic-data-generator.git@main data-designer-mcp
```
Or locally via CLI:
```bash
data-designer <preview|create|validate|agent>
```

## Available MCP Tools

When connected to `data-designer-mcp`:
1. `introspect_catalog`: Discover samplers, column types, validators, processors, personas, and model endpoints.
2. `scaffold_builder_script`: Generate a starting PEP 723 Python script for any domain.
3. `validate_builder`: Run sub-second static analysis and schema validation on a Python script or YAML config.
4. `preview_dataset`: Generate a 5-record sample with Markdown tables and column statistics for rapid quality iteration.
5. `generate_dataset`: Perform full batch generation and export to Parquet, JSONL, or CSV.
6. `export_to_bigquery`: Load generated Parquet dataset files into BigQuery tables with partitioning/clustering.

## Autonomous 4-Stage Workflow

Follow these 4 stages in sequence:

```mermaid
graph LR
    A[1. Architect Domain] --> B[2. Engineer Script]
    B --> C[3. Preview & Audit]
    C --> D[4. Generate & Export]
```

### 1. Architectural Modeling (`data-designer-architect`)
- Break down the request into entities: Dimensions (e.g. Customers, Merchants) and Facts (e.g. Accounts, Cards, Transactions).
- Establish cardinality ratios and foreign key dependencies.
- Select realistic statistical distributions (Category weights, Uniform bounds, Faker personas).

### 2. Script Authoring (`data-designer-engineer`)
- Call `scaffold_builder_script` or write a Python script with PEP 723 metadata and a `load_config_builder() -> dd.DataDesignerConfigBuilder` function.
- Call `validate_builder(script_content=...)` to ensure all column types, sampler params, and Jinja2 expressions compile.

### 3. Preview & Quality Audit (`data-designer-evaluator`)
- Call `preview_dataset(script_content=..., num_records=5)`.
- Review the returned Markdown table and `column_stats`:
  - Are null rates zero where expected?
  - Are primary keys 100% unique?
  - Are values realistic for the domain?
- If issues exist, edit the script and re-run `preview_dataset`.

### 4. Generation & Database Export
- Call `generate_dataset(script_content=..., num_records=N, output_format="parquet")`.
- If exporting to BigQuery, call `export_to_bigquery(source_path=..., project_id=..., dataset_id=...)`.
- If BigQuery MCP is present, query `__TABLES__` to confirm record counts.

## Common Pitfalls & Rules
- **Category Sampler**: Takes `values=["A", "B"]` and optional `weights=[0.8, 0.2]`.
- **Uniform Sampler**: Takes `low=0.0` and `high=100.0`.
- **Person Faker**: Use `sampler_type="person_from_faker"` with `drop=True` for intermediate extraction.
- **Jinja2 Referencing**: Use `{{ column_name }}`. For objects, use `{{ person.first_name }}`. For judge scores, use `{{ judge_col.metric.score }}`.
