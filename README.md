<p align="center">
  <img src="RgbFinanceWeb/wwwroot/images/logo.png" alt="RGB Finance" height="80" />
</p>

<h1 align="center">RGB Investing</h1>

<p align="center">
  Deep learning-based BUY/SELL signal generator for stock markets.
  <br />
  Converts market data into visual patterns and learns indicator combinations automatically.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/.NET-10.0-512BD4?style=flat&logo=dotnet&logoColor=white" />
  <img src="https://img.shields.io/badge/TensorFlow-2.x-FF6F00?style=flat&logo=tensorflow&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/SQL_Server-Express-CC2927?style=flat&logo=microsoftsqlserver&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-7.0-DC382D?style=flat&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/Airflow-2.7-017CEE?style=flat&logo=apacheairflow&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/MLflow-Tracking-0194E2?style=flat&logo=mlflow&logoColor=white" />
</p>

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Model](#model)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Airflow DAGs](#airflow-dags)
- [API Reference](#api-reference)

---

## Overview

RGB Finance takes a different approach to technical analysis. Instead of asking investors to choose and tune indicators manually, it lets a deep learning model learn which indicator combinations are predictive automatically, across hundreds of stocks.

The core idea: convert 400 or 900 days of OHLCV data into 16 independent technical indicators, reshape them into a 20×20 or 30x30 grid (like an image), and train a CNN to recognize patterns that historically preceded price movements.

Markets covered: **S&P 500**, **NASDAQ 100**, **BIST 100**

---

## Architecture

```
User (Browser)
      |
ASP.NET Razor Pages (Web UI)
      |
FastAPI (Python ML API)
      |
      +-- TensorFlow CNN Model
      +-- Redis Cache
      +-- MLflow (Experiment Tracking)
      |
SQL Server (Users, Portfolio, Predictions)
      |
Apache Airflow (Docker)
      +-- daily_predict_bist100     (15:00 UTC, Mon-Fri)
      +-- daily_predict_us          (21:00 UTC, Mon-Fri)
      +-- daily_drift_monitor       (22:00 UTC, Mon-Fri)
      +-- monthly_optuna_retrain    (1st of month, 16:00 UTC)
```

---

## Model

The model architecture:

```
Input (20×20×16)
  → TimeDistributed(Dense(3))     # Learned RGB projection
  → Conv2D(32) + BN + SE-block    # dilation (1,1)
  → Conv2D(64) + BN + SE-block    # dilation (2,1)
  → MaxPool(2,2)
  → Conv2D(64) + BN + SE-block    # dilation (4,1)
  → MaxPool(2,2)
  → GlobalAveragePooling2D
  → Dropout(0.5)
  → Dense(1, sigmoid)
```

**Training strategy:** Global model trained on SP500 (500+ stocks), then fine-tuned per market using only the projection and output layers (113 trainable parameters during fine-tune). This preserves universal pattern knowledge while adapting to market-specific dynamics.

**Indicators used (16):**

| Category | Indicators |
|---|---|
| Raw | log_return, volatility, volume_ratio |
| Momentum | rsi_14, stoch, mfi, cci, roc |
| Trend | macd, macd_signal, adx, vwap_ratio |
| Volatility | bb_pct, bb_width, atr |
| Volume | obv_ratio |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web UI | ASP.NET Razor Pages (.NET 10) |
| ML API | FastAPI + Uvicorn |
| Model | TensorFlow / Keras CNN |
| Data | yfinance |
| Cache | Redis 7 |
| Database | SQL Server Express |
| Experiment Tracking | MLflow |
| Hyperparameter Search | Optuna |
| Scheduler | Apache Airflow 2.7 (Docker) |
| Auth | ASP.NET Identity + TOTP 2FA |
| Stock Search | Finnhub API |

---

## Getting Started

### Prerequisites

- Python 3.12
- .NET 10 SDK
- SQL Server Express
- Docker Desktop

### 1. Clone and configure

```bash
git clone https://github.com/atasoyturk/deep_rgb_encoding_for_finance.git
cd deep_rgb_encoding_for_finance
cp .env.example .env
# Fill in .env with your values
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Redis

```bash
docker-compose -f docker-compose-redis.yml up -d
```

### 4. Start Airflow

```bash
docker-compose -f airflow-official.yaml up airflow-init
docker-compose -f airflow-official.yaml up -d
```

### 5. Train initial models

Open the web UI (step 7), go to **Train** page as admin:
- Train global model (SP500, fine_tune: off)
- Fine-tune NASDAQ100 (fine_tune: on)
- Fine-tune BIST100 (fine_tune: on)

### 6. Start the ML API

```bash
uvicorn api.main:app --reload --port 8000
```

### 7. Start the web application

```bash
cd RgbFinanceWeb
dotnet ef database update
dotnet watch
```

Open `http://localhost:5175`

---

## Project Structure

```
.
├── api/                    # FastAPI application
│   ├── main.py             # Endpoints
│   ├── predictor.py        # Model inference
│   ├── cache.py            # Redis cache layer
│   └── schemas.py          # Pydantic models
├── src/                    # Core ML pipeline
│   ├── data.py             # yfinance data fetching
│   ├── features.py         # 16 technical indicators
│   ├── normalization.py    # QuantileScaler
│   ├── builder.py          # Experiment builder
│   ├── model.py            # CNN architecture
│   ├── experiment.py       # Training orchestration
│   ├── dataset.py          # Sliding window dataset
│   ├── optimize.py         # Optuna search
│   ├── tickers.py          # Market ticker lists
│   └── experiment_config.py
├── dags/                   # Airflow DAGs
│   ├── daily_predict_dag.py
│   ├── drift_monitor_dag.py
│   └── optuna_dag.py
├── RgbFinanceWeb/          # ASP.NET web application
│   ├── Pages/              # Razor Pages
│   ├── Data/               # EF Core DbContext
│   ├── Models/             # View models
│   └── Endpoints/          # Minimal API endpoints
├── config.py               # Project configuration
├── .env.example            # Environment variable template
├── docker-compose-redis.yml
└── airflow-official.yaml
```

---

## Airflow DAGs

| DAG | Schedule | Description |
|---|---|---|
| `daily_predict_bist100` | Mon-Fri 15:00 UTC | Update BIST100 signal cache + save predictions |
| `daily_predict_us` | Mon-Fri 21:00 UTC | Update SP500 + NASDAQ100 cache + save predictions |
| `daily_drift_monitor` | Mon-Fri 22:00 UTC | Evaluate past predictions, detect model drift |
| `monthly_optuna_retrain` | 1st of month 16:00 UTC | Optuna search + global train + fine-tune all markets |

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Model status |
| GET | `/signals?market=SP500` | All signals for a market |
| GET | `/signals/{ticker}?market=SP500` | Signal for a specific ticker |
| GET | `/gradcam/{ticker}?market=SP500` | Grad-CAM heatmap (PNG) |
| GET | `/weights_json?market=SP500` | Learned projection weights |
| GET | `/indicators/{market}` | Indicator importance ranking |
| GET | `/model/history/{market}` | Training run history |
| POST | `/train` | Trigger model training |
| GET | `/train/{job_id}` | Training job status |
| POST | `/predictions/save?market=SP500` | Save daily predictions |
| POST | `/api/drift/check?market=SP500` | Evaluate prediction accuracy |

---

<p align="center">
  Built with a focus on interpretability and reproducibility.
</p>