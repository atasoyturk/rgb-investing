from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from airflow import DAG
from airflow.operators.python import PythonOperator

import os

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

GMAIL_USER     = os.environ["AIRFLOW_GMAIL_USER"]
GMAIL_PASSWORD = os.environ["AIRFLOW_GMAIL_PASSWORD"]
NOTIFY_TO      = os.environ["AIRFLOW_NOTIFY_TO"]


def send_email(subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_TO
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(GMAIL_USER, GMAIL_PASSWORD)
        s.sendmail(GMAIL_USER, [NOTIFY_TO], msg.as_string())


def check_drift(market: str, **kwargs):
    import requests

    r      = requests.post(
        f"http://178.104.125.39:5175/api/drift/check?market={market}",
        timeout=60
    )
    result = r.json()
    print(f"{market} drift check: {result}")

    accuracy = result.get("accuracy")
    if accuracy is not None and accuracy < 0.45:
        print(f"DRIFT DETECTED for {market}! Accuracy: {accuracy:.2%}")

        # Email gönder
        send_email(
            subject=f"[RGB Investing] Model drift tespit edildi, modelin performansı düştü — {market}",
            body=(
                f"Market: {market}\n"
                f"Accuracy: {accuracy:.2%}\n"
                f"Threshold: 45%\n\n"
                f"Otomatik yeniden model eğitimi tetiklendi."
            )
        )

        # Retrain tetikle
        trigger = requests.post(
            "http://178.104.125.39:8000/train",
            json={"market": market},
            timeout=30
        )
        print(f"Retrain triggered: {trigger.status_code}")


with DAG(
    dag_id="weekly_drift_monitor",
    default_args=default_args,
    description="Weekly model drift monitoring",
    schedule_interval="0 22 * * 5",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ml", "monitoring"],
) as dag:

    sp500_task = PythonOperator(
        task_id="check_sp500_drift",
        python_callable=check_drift,
        op_kwargs={"market": "SP500"},
    )

    nasdaq_task = PythonOperator(
        task_id="check_nasdaq100_drift",
        python_callable=check_drift,
        op_kwargs={"market": "NASDAQ100"},
    )

    bist_task = PythonOperator(
        task_id="check_bist100_drift",
        python_callable=check_drift,
        op_kwargs={"market": "BIST100"},
    )

    sp500_task >> nasdaq_task >> bist_task