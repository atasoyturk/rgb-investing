import io, os, sys, logging, random
import numpy as np
import tensorflow as tf
import optuna
import mlflow

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("mlflow").setLevel(logging.ERROR)
optuna.logging.set_verbosity(optuna.logging.WARNING)

from config import RANDOM_SEED, MLFLOW_TRACKING_URI
from src.data import fetch_data
from src.features import FeatureBuilder, FEATURE_CATALOG
from src.experiment import RGBExperiment
from src.builder import _apply_scaler
from src.experiment_config import ExperimentConfig

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
tf.random.set_seed(RANDOM_SEED)

ALL_FEATURES = list(FEATURE_CATALOG.keys())
DB_PATH      = os.getenv("OPTUNA_DB_PATH", "sqlite:///optuna.db")


def run_optimization(
    market:     str,
    tickers:    list,
    start_date: str,
    end_date:   str,
    n_trials:   int = 20,
) -> dict:
    """
    Run Optuna optimization for a given market.
    Returns best params: {window_size, future_days, stride}
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(f"optuna-{market.lower()}")

    print(f"\n[Optuna] Loading data for {market}...")
    data    = fetch_data(tickers=tickers, start=start_date, end=end_date)
    builder = FeatureBuilder(data)
    tickers = list(data["Ticker"].unique())

    build_plan  = {"R": ALL_FEATURES, "G": ALL_FEATURES, "B": ALL_FEATURES}
    df_features = builder.build_custom(build_plan)

    trial_count = [0]
    best_f1     = [0.0]

    def objective(trial) -> float:
        
        threshold   = trial.suggest_float("label_threshold", 0.000, 0.030, step=0.002)
        window_size = 400
        future_days = trial.suggest_categorical("future_days", [3, 4, 5])
        stride      = trial.suggest_categorical("stride",      [3, 5, 10])
        h           = int(np.sqrt(window_size))

        cfg = ExperimentConfig(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            window_size=window_size,
            future_days=future_days,
            stride=stride,
        )

        scaled_df, scaler = _apply_scaler(df_features, ALL_FEATURES, tickers, cfg.train_split)

        exp = RGBExperiment(
            name=f"{market}_{h}x{h}_fd{future_days}_s{stride}",
            df=scaled_df,
            scaler=scaler,
            feature_cols=ALL_FEATURES,
            window_size=window_size,
            future_days=future_days,
            stride=stride,
            label_threshold=threshold
        )

        captured = io.StringIO()
        sys.stdout = captured
        try:
            exp.prepare_data()
        finally:
            sys.stdout = sys.__stdout__

        exp.train()

        sys.stdout = captured
        try:
            exp.evaluate()
        finally:
            sys.stdout = sys.__stdout__

        trial_count[0] += 1
        status = ""
        if exp.f1_macro > best_f1[0]:
            best_f1[0] = exp.f1_macro
            status = "  *** NEW BEST ***"

        print(
            f"  [Optuna/{market}] Trial {trial_count[0]:>3} | {h}x{h} | "
            f"future={future_days:>2}d  stride={stride:>2} | "
            f"F1={exp.f1_macro:.4f}{status}"
        )
        return exp.f1_macro

    study_name = f"{market.lower()}_optuna"
    study = optuna.create_study(
        study_name=study_name,
        storage=DB_PATH,
        load_if_exists=True,
        direction="maximize",
        sampler=optuna.samplers.TPESampler(n_startup_trials=5, seed=RANDOM_SEED),
    )

    print(f"[Optuna] Starting {n_trials} trials for {market}...")
    study.optimize(objective, n_trials=n_trials)

    best = study.best_params
    print(f"[Optuna] Best params for {market}: {best}")
    return best