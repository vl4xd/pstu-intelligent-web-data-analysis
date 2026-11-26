import pandera as pa
from pandera import Column, Check

# Контракт данных (Data Contract)
item_schema = pa.DataFrameSchema({
    "id": Column(int, unique=True, nullable=False),
    "title": Column(str, Check.str_length(1, 500), nullable=False),
    "price": Column(float, Check.ge(0), nullable=False),
    "updated_at": Column("datetime64[ns]", nullable=False),
})