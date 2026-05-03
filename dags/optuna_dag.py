from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}

def run_optuna(market: str, **kwargs):
    import sys
    sys.path.insert(0, '/opt/airflow')
    
    from datetime import datetime, timedelta
    from src.optimize import run_optimization
    from src.tickers import MARKET_TICKERS

    today      = datetime.now().strftime('%Y-%m-%d')
    ten_ago    = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
    tickers    = MARKET_TICKERS[market]

    best_params = run_optimization(
        market=market,
        tickers=tickers,
        start_date=ten_ago,
        end_date=today,
        n_trials=20,
    )
    
    # XCom ile sonraki task'a aktar
    kwargs['ti'].xcom_push(key=f'best_params_{market}', value=best_params)
    print(f"[Optuna] {market} best: {best_params}")


def trigger_retrain_with_best_params(market: str, **kwargs):
    import requests
    
    ti          = kwargs['ti']
    best_params = ti.xcom_pull(key=f'best_params_{market}')
    
    from datetime import datetime, timedelta
    today   = datetime.now().strftime('%Y-%m-%d')
    ten_ago = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')

    is_global   = market == "SP500"
    fine_tune   = not is_global
    name        = "global_model" if is_global else f"{market.lower()}_finetune"

    payload = {
        "name":        name,
        "market":      market,
        "tickers":     [],
        "start_date":  ten_ago,
        "end_date":    today,
        "window_size": best_params.get("window_size", 400),
        "future_days": best_params.get("future_days", 5),
        "stride":      best_params.get("stride", 5),
        "fine_tune":   fine_tune,
    }
    r = requests.post("http://host.docker.internal:8000/train", json=payload, timeout=30)
    print(f"{market} retrain triggered with best params: {r.json()}")


with DAG(
    dag_id="monthly_optuna_retrain",
    default_args=default_args,
    description="Monthly Optuna optimization then retrain",
    schedule_interval="0 16 1 * *",  # Her ayın 1'i 16:00 UTC — eski retrain DAG'ından 2 saat önce
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ml", "optuna", "retrain"],
) as dag:

    # SP500 — global model
    sp500_optuna = PythonOperator(
        task_id="optuna_sp500",
        python_callable=run_optuna,
        op_kwargs={"market": "SP500"},
    )
    sp500_retrain = PythonOperator(
        task_id="retrain_sp500",
        python_callable=trigger_retrain_with_best_params,
        op_kwargs={"market": "SP500"},
    )

    # NASDAQ100 — fine-tune
    nasdaq_optuna = PythonOperator(
        task_id="optuna_nasdaq100",
        python_callable=run_optuna,
        op_kwargs={"market": "NASDAQ100"},
    )
    nasdaq_retrain = PythonOperator(
        task_id="retrain_nasdaq100",
        python_callable=trigger_retrain_with_best_params,
        op_kwargs={"market": "NASDAQ100"},
    )

    # BIST100 — fine-tune
    bist_optuna = PythonOperator(
        task_id="optuna_bist100",
        python_callable=run_optuna,
        op_kwargs={"market": "BIST100"},
    )
    bist_retrain = PythonOperator(
        task_id="retrain_bist100",
        python_callable=trigger_retrain_with_best_params,
        op_kwargs={"market": "BIST100"},
    )

    # Sıra: SP500 optuna → retrain → NASDAQ optuna → retrain → BIST optuna → retrain
    sp500_optuna >> sp500_retrain >> nasdaq_optuna >> nasdaq_retrain >> bist_optuna >> bist_retrain