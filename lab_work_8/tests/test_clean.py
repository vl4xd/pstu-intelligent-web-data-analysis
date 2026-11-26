import pandas as pd
from datetime import datetime
from pipeline.clean import clean_data

def test_clean_quarantine_bad_data():
    raw_df = pd.DataFrame([
        {"id": 1, "title": "Good", "price": "10.50", "updated_at": datetime.now()},
        {"id": 2, "title": "Bad", "price": "not_a_number", "updated_at": datetime.now()}
    ])
    clean_df, quarantine_df = clean_data(raw_df)
    
    assert len(clean_df) == 1
    assert len(quarantine_df) == 1
    assert clean_df.iloc[0]["price"] == 10.50