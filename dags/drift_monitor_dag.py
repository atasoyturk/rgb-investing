from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def check_drift(market: str, **kwargs):
    import requests
    
    r = requests.post(
        f"http://178.104.125.39:5175/api/drift/check?market={market}",
        timeout=60
    )
    result = r.json()
    print(f"{market} drift check: {result}")
    
    if result.get("accuracy") and result["accuracy"] < 0.45:
        print(f"DRIFT DETECTED for {market}! Accuracy: {result['accuracy']:.2%}")


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