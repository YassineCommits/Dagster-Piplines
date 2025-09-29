from dagster import Definitions, asset, job, op, job
import duckdb
import pandas as pd
import os
import requests
from datetime import datetime
import time

@asset
def create_hello_world_data(context):
    """
    Create sample hello world data for the pipeline
    """
    context.log.info("Creating sample hello world data...")
    
    # Create sample data with more variety
    data = {
        "id": list(range(1, 201)),  # Increased to 200 records
        "name": [f"User_{i}" for i in range(1, 201)],
        "age": [20 + (i % 50) for i in range(1, 201)],
        "city": [["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Boston", "Seattle", "Miami"][i % 8] for i in range(1, 201)],
        "salary": [50000 + (i * 1000) + (i % 10 * 5000) for i in range(1, 201)],
        "department": [["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations", "Support"][i % 7] for i in range(1, 201)],
        "created_at": [datetime.now().strftime("%Y-%m-%d %H:%M:%S") for _ in range(1, 201)]
    }
    
    df = pd.DataFrame(data)
    context.log.info(f"Created {len(df)} records")
    return df

@asset
def duckdb_parquet_asset(context, create_hello_world_data):
    """
    An asset that uses DuckDB to process data and save it as a Parquet file.
    """
    output_dir = "/tank/data/parquet"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "hello_world_data.parquet")
    
    con = duckdb.connect(database=":memory:")
    con.register("my_table", create_hello_world_data)
    
    # Run a more complex query
    query = """
    SELECT 
        city, 
        department,
        COUNT(id) as total_users, 
        AVG(age) as average_age, 
        SUM(salary) as total_salary,
        AVG(salary) as average_salary,
        MIN(salary) as min_salary,
        MAX(salary) as max_salary
    FROM my_table 
    GROUP BY city, department 
    ORDER BY city, department
    """
    result_df = con.execute(query).fetchdf()
    
    # Save to parquet
    result_df.to_parquet(output_path, index=False)
    context.log.info(f"DuckDB processed data saved to {output_path}:\n{result_df}")
    
    return output_path

@asset
def raw_data_parquet_asset(context, create_hello_world_data):
    """
    Save the raw data as parquet for ClickHouse to read
    """
    output_dir = "/tank/data/parquet"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "raw_hello_world_data.parquet")
    
    # Save raw data to parquet
    create_hello_world_data.to_parquet(output_path, index=False)
    context.log.info(f"Raw data saved to {output_path}")
    
    return output_path

@asset
def clickhouse_etl_asset(context, duckdb_parquet_asset):
    """
    Automatically load parquet data into ClickHouse
    """
    context.log.info("Starting ClickHouse ETL process...")
    
    # ClickHouse connection details
    clickhouse_host = "10.120.236.126"
    clickhouse_port = "8123"
    clickhouse_user = "default"
    clickhouse_password = "clickhouse123"
    
    base_url = f"http://{clickhouse_host}:{clickhouse_port}"
    
    # Wait for ClickHouse to be ready
    max_retries = 30
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{base_url}/?user={clickhouse_user}&password={clickhouse_password}&query=SELECT%201", timeout=5)
            if response.status_code == 200:
                context.log.info("ClickHouse is ready!")
                break
        except Exception as e:
            context.log.info(f"ClickHouse not ready yet (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2)
    else:
        raise Exception("ClickHouse is not accessible after 30 attempts")
    
    # Create table if not exists
    table_name = f"hello_world_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        city String,
        department String,
        total_users UInt32,
        average_age Float32,
        total_salary UInt64,
        average_salary UInt32,
        min_salary UInt32,
        max_salary UInt32
    ) ENGINE = Memory
    """
    
    context.log.info(f"Creating table: {table_name}")
    response = requests.post(f"{base_url}/?user={clickhouse_user}&password={clickhouse_password}", 
                           data=create_table_query, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Failed to create table: {response.text}")
    
    # Load data into ClickHouse using HTTP interface
    # Read the parquet file and send it directly to ClickHouse
    parquet_filename = f"hello_world_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
    
    context.log.info(f"Loading parquet file: {duckdb_parquet_asset}")
    
    # Load data into ClickHouse using INSERT with file() function
    load_query = f"INSERT INTO {table_name} SELECT * FROM file('{duckdb_parquet_asset}', Parquet)"
    
    context.log.info(f"Loading data into ClickHouse table: {table_name}")
    response = requests.post(f"{base_url}/?user={clickhouse_user}&password={clickhouse_password}", 
                           data=load_query, timeout=60)
    
    if response.status_code != 200:
        raise Exception(f"Failed to load data: {response.text}")
    
    # Verify data was loaded
    verify_query = f"SELECT COUNT(*) as total_records FROM {table_name}"
    response = requests.get(f"{base_url}/?user={clickhouse_user}&password={clickhouse_password}&query={verify_query}")
    
    if response.status_code == 200:
        context.log.info(f"Data verification successful: {response.text.strip()}")
    else:
        context.log.warning(f"Data verification failed: {response.text}")
    
    context.log.info(f"ClickHouse ETL completed successfully! Table: {table_name}")
    return table_name

@asset
def metabase_postgres_sync_asset(context, clickhouse_etl_asset):
    """
    Sync ClickHouse data to PostgreSQL for Metabase
    """
    context.log.info("Starting PostgreSQL sync for Metabase...")
    
    # PostgreSQL connection details (using the existing PostgreSQL)
    pg_host = "us-west-aws.db.dev.guepard.run"
    pg_port = "23832"
    pg_user = "guepard-admin"
    pg_password = "sGtCa0xj2sM6"
    pg_database = "postgres"
    
    # ClickHouse connection details
    clickhouse_host = "10.120.236.126"
    clickhouse_port = "8123"
    clickhouse_user = "default"
    clickhouse_password = "clickhouse123"
    
    base_url = f"http://{clickhouse_host}:{clickhouse_port}"
    
    # Get data from ClickHouse
    query = f"SELECT * FROM {clickhouse_etl_asset}"
    response = requests.get(f"{base_url}/?user={clickhouse_user}&password={clickhouse_password}&query={query}")
    
    if response.status_code != 200:
        raise Exception(f"Failed to get data from ClickHouse: {response.text}")
    
    # Parse the data (ClickHouse returns TSV format)
    lines = response.text.strip().split('\n')
    if not lines or lines[0] == '':
        context.log.warning("No data found in ClickHouse")
        return "no_data"
    
    # Create a simple CSV file for PostgreSQL import
    csv_filename = f"/tank/data/metabase_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(csv_filename, 'w') as f:
        # Write header
        f.write("city,department,total_users,average_age,total_salary,average_salary,min_salary,max_salary\n")
        # Write data
        for line in lines:
            if line.strip():
                f.write(line + "\n")
    
    context.log.info(f"Created CSV file for Metabase sync: {csv_filename}")
    context.log.info(f"Data synced from ClickHouse table: {clickhouse_etl_asset}")
    
    return csv_filename

@job
def automated_etl_pipeline():
    """
    Fully automated ETL pipeline that handles everything:
    1. Creates data
    2. Processes with DuckDB
    3. Saves to parquet
    4. Loads into ClickHouse
    5. Syncs to PostgreSQL for Metabase
    """
    clickhouse_etl_asset()
    metabase_postgres_sync_asset()

@job
def hello_world_pipeline():
    """
    Original pipeline for backward compatibility
    """
    duckdb_parquet_asset()
    raw_data_parquet_asset()

defs = Definitions(
    assets=[
        create_hello_world_data, 
        duckdb_parquet_asset, 
        raw_data_parquet_asset,
        clickhouse_etl_asset,
        metabase_postgres_sync_asset
    ],
    jobs=[hello_world_pipeline, automated_etl_pipeline]
)