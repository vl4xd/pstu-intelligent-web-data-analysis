import sys
import os
import time # <-- ДОБАВИЛИ
from datetime import datetime, timedelta
from airflow.decorators import dag, task
import logging

sys.path.insert(0, '/opt/airflow')

from pipeline.io import setup_logging
from pipeline.collect import collect_data
from pipeline.clean import clean_data
from pipeline.load import load_data
from pipeline.report import generate_report

log = setup_logging()

default_args = {
    'owner': 'student',
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
}

@dag(
    dag_id='daily_pipeline',
    default_args=default_args,
    schedule='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['lab8', 'production'],
)
def pipeline_dag():
    
    @task(execution_timeout=timedelta(minutes=30))
    def task_collect():
        return collect_data()
        
    @task
    def task_clean(df):
        return clean_data(df)
        
    @task
    def task_load(clean_tuple):
        clean_df, _ = clean_tuple
        load_data(clean_df)

    @task
    def task_report(clean_tuple):
        start_time = time.time() # <-- ЗАМЕР ВРЕМЕНИ
        clean_df, quarantine_df = clean_tuple
        generate_report(clean_df, quarantine_df, start_time)
        
    raw_data = task_collect()
    cleaned_data = task_clean(raw_data)
    
    task_load(cleaned_data)
    task_report(cleaned_data)

pipeline_dag()