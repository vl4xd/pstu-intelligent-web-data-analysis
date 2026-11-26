FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем пользователя
RUN useradd -m appuser

# Создаем папку для Airflow и даем права нашему пользователю
RUN mkdir -p /opt/airflow && chown -R appuser:appuser /opt/airflow

# Даем права на папку с нашим приложением
RUN chown -R appuser:appuser /app

# Безопасность: не запускаем от root (слайд 13)
USER appuser

CMD ["python", "-c", "print('Pipeline container ready')"]