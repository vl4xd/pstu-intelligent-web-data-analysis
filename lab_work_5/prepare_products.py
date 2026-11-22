import os

import pandas as pd
from datasets import load_dataset

print("Загрузка датасета nyuuzyou/PM-products...")
# Загружаем только тренировочную часть
ds = load_dataset("nyuuzyou/PM-products", split="train")

# Чтобы не грузить все 500к строк в память, перемешаем и возьмем первые 2000
# (нам нужно 250, но возьмем с запасом на случай пустых описаний)
ds_sample = ds.shuffle(seed=42).select(range(2000))

# Конвертируем в pandas
df = pd.DataFrame(ds_sample)

print(f"Исходное количество записей: {len(df)}")

# Оставляем только те товары, где есть хотя бы какое-то описание
df = df.dropna(subset=['description', 'longDescription'], how='all')
df = df[df['description'].str.strip().astype(bool) | df['longDescription'].str.strip().astype(bool)]

print(f"Записей с описанием: {len(df)}")

# Берем ровно 250 записей
df_final = df.head(300).copy()

# Оставляем только нужные колонки
df_final = df_final[['name', 'description', 'longDescription', 'brand', 'providerName']]

# Заполняем пустые значения, чтобы не было ошибок при склейке
df_final = df_final.fillna('')

# Сохраняем
os.makedirs('data', exist_ok=True)
df_final.to_csv('data/products.csv', index=False, encoding='utf-8')

print("✅ Файл data/products.csv успешно создан!")
print(f"Размер выборки: {len(df_final)} товаров.")