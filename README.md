# Dagster Pipelines Repository

This repository contains Dagster data pipelines for the Guepard platform.

## Pipeline Structure

- `pipelines/hello_world_pipeline/` - Hello World pipeline with DuckDB processing
- `pipelines/setup.py` - Python package configuration
- `Dockerfile` - Container image for running pipelines

## Hello World Pipeline

The hello world pipeline demonstrates:
- Data generation (100 sample user records)
- DuckDB processing and aggregation
- Parquet file output for ClickHouse consumption
- Integration with Nomad orchestration

## Usage

The pipeline is designed to run in Nomad with:
- Volume mount to `/tank/data` for output files
- Integration with ClickHouse, Metabase, and Cube.js
- Automated deployment from Git repository

## Dependencies

- Dagster 1.7.3
- DuckDB
- Pandas
- PyArrow
- PostgreSQL (for Dagster metadata)
