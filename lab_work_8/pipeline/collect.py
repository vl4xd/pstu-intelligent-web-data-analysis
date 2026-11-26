import pandas as pd
import logging
from datetime import datetime

log = logging.getLogger("pipeline.collect")

def collect_data() -> pd.DataFrame:
    log.info("Starting data collection...")
    # Имитация сырых данных (в реальности здесь был бы requests.get)
    raw_data = [
        {"id": 1, "title": "Laptop", "price": "1200.50", "updated_at": datetime.now()},
        {"id": 2, "title": "Mouse", "price": "25.00", "updated_at": datetime.now()},
        {"id": 3, "title": "Keyboard", "price": "bad_price", "updated_at": datetime.now()}, # Битая запись
        {"id": 4, "title": "Monitor", "price": "300.00", "updated_at": datetime.now()}
    ]
    df = pd.DataFrame(raw_data)
    log.info(f"Collected {len(df)} raw records.")
    return df