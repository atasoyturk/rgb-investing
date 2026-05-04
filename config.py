import os
from dotenv import load_dotenv

load_dotenv()

# --- MLflow ---
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "deep-rgb-finance")
MLFLOW_TRACKING_URI    = os.getenv("MLFLOW_TRACKING_URI", "mlruns")

# --- Labeling ---
CLASS_WEIGHT_MULTIPLIER = 1.0

# --- Sliding window defaults ---
WINDOW_SIZE = 400
STRIDE      = 5
TRAIN_SPLIT = 0.8
FUTURE_DAYS = 5

# --- Normalization ---
LOG_RETURN_CLIP = 0.05
VOLATILITY_CLIP = 0.1
VOLUME_CLIP     = 1.0

# --- Model ---
BATCH_SIZE   = 32
EPOCHS       = 100
PATIENCE     = 10
DROPOUT_RATE = 0.5
RANDOM_SEED  = 42