import pandas as pd
import logging
import json
import os
import time

log = logging.getLogger("pipeline.report")

def send_alert(message: str):
    """Имитация отправки алерта в Telegram/Slack (Слайд 11)"""
    log.error(f"🚨 ALERT TO CHAT: {message}")

def generate_report(df: pd.DataFrame, quarantine_df: pd.DataFrame, start_time: float):
    # Считаем время выполнения (Слайд 11)
    duration_s = time.time() - start_time
    
    # Считаем условную стоимость (Слайд 12: стоимость прогона)
    cpu_cost_per_sec = 0.00001 # условная цена
    estimated_cost = duration_s * cpu_cost_per_sec

    # Сбор метрик (слайд 9)
    metrics = {
        "event": "pipeline_report",
        "rows_in": len(df) + len(quarantine_df),
        "rows_out": len(df),
        "quarantined": len(quarantine_df),
        "duration_s": round(duration_s, 2),
        "estimated_cost_usd": round(estimated_cost, 4)
    }
    log.info(json.dumps(metrics))
    
    # Алерт при пустом результате (Слайд 8)
    if len(df) == 0:
        send_alert("Пайплайн завершился успешно, но результат пустой! Проверьте источники.")
    
    # Сохраняем отчет в файл (для дашборда)
    report_path = "/tmp/pipeline_report.csv"
    df.to_csv(report_path, index=False)
    log.info(f"Report saved to {report_path}")