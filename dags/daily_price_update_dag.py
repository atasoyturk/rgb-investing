from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def update_prices(market: str, **kwargs):
    import requests
    r = requests.post(
        f"http://178.104.125.39:8000/prices/update?market={market}",
        timeout=60
    )
    print(f"{market} prices updated: {r.json()}")

with DAG(
    dag_id="daily_price_update",
    default_args=default_args,
    description="Daily price update for all markets",
    schedule_interval="0 16 * * 1-5",  # Hafta içi 16:00 UTC (19:00 Türkiye)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ml", "price", "daily"],
) as dag:

    bist_task = PythonOperator(
        task_id="update_bist100_prices",
        python_callable=update_prices,
        op_kwargs={"market": "BIST100"},
    )

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

    bist_task >> sp500_task >> nasdaq_task