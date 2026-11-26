import pandas as pd
import logging
from sqlalchemy import create_engine, text
import os

log = logging.getLogger("pipeline.load")

def load_data(df: pd.DataFrame, table_name: str = "items"):
    if df.empty:
        log.warning("DataFrame is empty, skipping load.")
        return

    db_url = os.getenv("DB_URL", "postgresql://airflow:airflow@localhost:5432/airflow")
    engine = create_engine(db_url)
    
    log.info(f"Loading {len(df)} records to {table_name} (upsert)...")
    
    # Используем UPSERT для идемпотентности
    records = df.to_dict('records')
    with engine.begin() as conn:
        for row in records:
            conn.execute(
                text("""
                    INSERT INTO items (id, title, price, updated_at) 
                    VALUES (:id, :title, :price, :updated_at)
                    ON CONFLICT (id) DO UPDATE 
                    SET title = EXCLUDED.title, 
                        price = EXCLUDED.price, 
                        updated_at = EXCLUDED.updated_at;
                """),
                row
            )
    log.info("Load completed successfully.")