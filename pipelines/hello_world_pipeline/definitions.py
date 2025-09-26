from dagster import Definitions, asset, job
import duckdb
import pandas as pd
import os
from datetime import datetime

@asset
def create_hello_world_data(context):
    """
    Create sample hello world data for the pipeline
    """
    context.log.info("Creating sample hello world data...")
    
    # Create sample data
    data = {
        "id": list(range(1, 101)),
        "name": [f"User_{i}" for i in range(1, 101)],
        "age": [20 + (i % 50) for i in range(1, 101)],
        "city": [["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"][i % 5] for i in range(1, 101)],
        "salary": [50000 + (i * 1000) for i in range(1, 101)],
        "department": [["Engineering", "Sales", "Marketing", "HR", "Finance"][i % 5] for i in range(1, 101)],
        "created_at": [datetime.now().strftime("%Y-%m-%d %H:%M:%S") for _ in range(1, 101)]
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
        AVG(salary) as average_salary
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

@job
def hello_world_pipeline():
    """
    Main pipeline that creates data and processes it with DuckDB
    """
    duckdb_parquet_asset()
    raw_data_parquet_asset()

defs = Definitions(
    assets=[create_hello_world_data, duckdb_parquet_asset, raw_data_parquet_asset],
    jobs=[hello_world_pipeline]
)
