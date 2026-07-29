from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def update_and_save(market: str, **kwargs):
    import requests
    api_key = Variable.get("internal_api_key_airflow", default_var=None)
    headers = {"X-Internal-Api-Key": api_key} if api_key else {}
    
    # 1. Cache güncelle
    r = requests.get(
        f"http://178.104.125.39:8000/signals?market={market}",
        headers=headers,
        timeout=120
    )
    print(f"{market} cache updated: {r.status_code}")
    
    # 2. Tahminleri kaydet
    r2 = requests.post(
        f"http://178.104.125.39:8000/predictions/save?market={market}&callback_url=http://178.104.125.39:5175/api/predictions",
        headers=headers,
        timeout=300
    )
    print(f"{market} predictions saved: {r2.json()}")


# BIST100 - 15:00 UTC
with DAG(
    dag_id="weekly_predict_bist100",
    default_args=default_args,
    description="BIST100 weekly prediction update + save",
    schedule_interval="0 15 * * 5",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ml", "predict", "bist"],
) as dag_bist:

    PythonOperator(
        task_id="update_bist100_predictions",
        python_callable=update_and_save,
        op_kwargs={"market": "BIST100"},
    )


# SP500 + NASDAQ100 - 21:00 UTC
with DAG(
    dag_id="weekly_predict_us",
    default_args=default_args,
    description="SP500 + NASDAQ100 weekly prediction update + save",
    schedule_interval="0 21 * * 5",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ml", "predict", "us"],
) as dag_us:

    sp500_task = PythonOperator(
        task_id="update_sp500_predictions",
        python_callable=update_and_save,
        op_kwargs={"market": "SP500"},
    )

    nasdaq_task = PythonOperator(
        task_id="update_nasdaq100_predictions",
        python_callable=update_and_save,
        op_kwargs={"market": "NASDAQ100"},
    )

    sp500_task >> nasdaq_task