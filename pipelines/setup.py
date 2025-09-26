from setuptools import setup, find_packages

setup(
    name="hello_world_pipeline",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "dagster==1.7.3",
        "dagster-postgres==0.23.3",
        "duckdb",
        "pandas",
        "numpy",
        "pyarrow",
    ],
    python_requires=">=3.8",
)
