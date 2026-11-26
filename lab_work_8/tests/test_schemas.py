import pytest
import pandas as pd
import pandera as pa
from datetime import datetime
from pipeline.schemas import item_schema

def test_schema_valid():
    df = pd.DataFrame([{
        "id": 1, "title": "Test", "price": 10.0, "updated_at": datetime.now()
    }])
    assert item_schema.validate(df) is not None

def test_schema_invalid_negative_price():
    df = pd.DataFrame([{
        "id": 1, "title": "Test", "price": -10.0, "updated_at": datetime.now()
    }])
    with pytest.raises(pa.errors.SchemaError):
        item_schema.validate(df)