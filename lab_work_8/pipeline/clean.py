import pandas as pd
import logging
from pipeline.schemas import item_schema
import pandera as pa

log = logging.getLogger("pipeline.clean")

def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    log.info("Starting data cleaning...")
    
    # Приведение типов (цена из строки в float)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    
    # Отделяем карантин (битые записи) от чистых данных
    clean_df = df.dropna(subset=["price"]).copy()
    quarantine_df = df[df["price"].isna()].copy()
    
    if not quarantine_df.empty:
        log.warning(f"Quarantined {len(quarantine_df)} bad records.")

    # Валидация схемы (Падает, если что-то не так)
    try:
        item_schema.validate(clean_df)
    except pa.errors.SchemaError as e:
        log.error(f"Schema validation failed: {e}")
        raise
        
    log.info(f"Cleaned data: {len(clean_df)} valid, {len(quarantine_df)} quarantined.")
    return clean_df, quarantine_df