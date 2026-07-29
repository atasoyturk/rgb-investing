from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def update_prices(market: str, **kwargs):
    import requests
    api_key = Variable.get("internal_api_key_airflow", default_var=None)
    headers = {"X-Internal-Api-Key": api_key} if api_key else {}
    r = requests.post(
        f"http://178.104.125.39:8000/prices/update?market={market}",
        headers=headers,
        timeout=60
    )
    print(f"{market} prices updated: {r.json()}")

# BIST100 - 15:30 UTC (kapanıştan 30 dk sonra)
with DAG(
    dag_id="daily_price_update_bist",
    default_args=default_args,
    description="Daily BIST100 price update",
    schedule_interval="30 15 * * 1-5",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["price", "daily", "bist"],
) as dag_bist:

    PythonOperator(
        task_id="update_bist100_prices",
        python_callable=update_prices,
        op_kwargs={"market": "BIST100"},
    )

# SP500 + NASDAQ - 21:30 UTC (kapanıştan 30 dk sonra)
with DAG(
    dag_id="daily_price_update_us",
    default_args=default_args,
    description="Daily SP500 + NASDAQ100 price update",
    schedule_interval="30 21 * * 1-5",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["price", "daily", "us"],
) as dag_us:

    sp500_task = PythonOperator(
        task_id="update_sp500_prices",
        python_callable=update_prices,
        op_kwargs={"market": "SP500"},
    )

    nasdaq_task = PythonOperator(
        task_id="update_nasdaq100_prices",
        python_callable=update_prices,
        op_kwargs={"market": "NASDAQ100"},
    )

    sp500_task >> nasdaq_task