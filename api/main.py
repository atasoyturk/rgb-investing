import os
import time
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import Response
from api.predictor import Predictor
from api.schemas import SignalResponse, SignalsTableResponse, HealthResponse, TrainRequest, ThresholdResponse
from api.cache import get_cached_signals, set_cached_signals, get_cached_gradcam, set_cached_gradcam, r, CACHE_TTL


from src.experiment_config import ExperimentConfig
from src.data import fetch_data
from src.features import FeatureBuilder, FEATURE_CATALOG
from src.builder import ExperimentBuilder

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

predictors: dict[str, Predictor] = {}
train_status: dict   = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictors
    print("[API] Starting...")
    from src.tickers import MARKET_TICKERS
    for market in MARKET_TICKERS.keys():
        path = "saved_model_global" if market == "SP500" else f"saved_model_{market.lower()}"
        try:
            predictors[market] = Predictor(model_path=path)
            print(f"[API] Loaded model: {market}")
        except FileNotFoundError:
            print(f"[API] No model found for {market}, skipping.")
    print("[API] Ready.")
    yield
    print("[API] Shutting down.")


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="RGB Finance API",
    description="BUY/SELL signal generator — Deep RGB Encoding for Finance",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from api.cache import get_cached_signals, set_cached_signals

@app.get("/signals", response_model=SignalsTableResponse, tags=["Signals"])
@limiter.limit("10/minute")
async def get_all_signals(request: Request, market: str = "SP500"):
    try:
        pred = predictors.get(market)
        if pred is None:
            raise HTTPException(status_code=404, detail=f"No model for market: {market}")

        # Cache'den oku
        cached = get_cached_signals(market)
        if cached:
            print(f"[Cache] HIT {market}")
            return SignalsTableResponse(
                signals=[SignalResponse(**s) for s in cached["signals"]],
                model_f1=cached.get("model_f1"),
                model_accuracy=cached.get("model_accuracy"),
            )

        # Cache yok — hesapla
        print(f"[Cache] MISS {market} — computing...")
        results = pred.predict_all()
        table   = SignalsTableResponse(
            signals=[SignalResponse(**r) for r in results],
            model_f1=pred.meta.get("f1_macro"),
            model_accuracy=pred.meta.get("accuracy"),
        )

        # Cache'e yaz
        set_cached_signals(market, {
            "signals":        [s.dict() for s in table.signals],
            "model_f1":       table.model_f1,
            "model_accuracy": table.model_accuracy,
        })

        return table

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/signals/{ticker}", response_model=SignalResponse, tags=["Signals"])
@limiter.limit("30/minute")
async def get_signal(request: Request, ticker: str, market: str = "SP500"):
    try:
        pred = predictors.get(market)
        if pred is None:
            raise HTTPException(status_code=404, detail=f"No model for market: {market}")
        return SignalResponse(**pred.predict(ticker.upper()))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/prices/update", tags=["System"])
@limiter.limit("5/minute")
async def update_prices(request: Request, market: str = "SP500"):
    try:
        cached = get_cached_signals(market)
        if not cached:
            raise HTTPException(status_code=404, detail="No cached signals found")
        
        tickers = [s["ticker"] for s in cached["signals"]]
        
        from src.data import fetch_data
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        
        data = fetch_data(tickers=tickers, start=yesterday, end=today)
        price_map = {}
        for ticker in tickers:
            tdf = data[data["Ticker"] == ticker]
            if not tdf.empty:
                price_map[ticker] = round(float(tdf["Close"].iloc[-1]), 2)
        
        for signal in cached["signals"]:
            if signal["ticker"] in price_map:
                signal["last_price"] = price_map[signal["ticker"]]
        
        set_cached_signals(market, cached)
        return {"updated": len(price_map)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/indicators/{market}", tags=["Visualisation"])
@limiter.limit("20/minute")
async def get_indicators(request: Request, market: str):
    try:
        pred = predictors.get(market)
        if pred is None:
            raise HTTPException(status_code=404, detail=f"No model for market: {market}")
        
        weights      = pred.model.layers[1].layer.layer.get_weights()[0]
        feature_cols = pred.meta["feature_cols"]
        
        result = []
        for i, name in enumerate(feature_cols):
            if i < weights.shape[0]:
                r = round(float(weights[i, 0]), 4)
                g = round(float(weights[i, 1]), 4)
                b = round(float(weights[i, 2]), 4)
                absolute = round(float(abs(r) + abs(g) + abs(b)), 4)
                result.append({
                    "name":     name,
                    "r":        r,
                    "g":        g,
                    "b":        b,
                    "absolute": absolute,
                })
        
        result.sort(key=lambda x: x["absolute"], reverse=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/threshold", response_model=ThresholdResponse, tags=["System"])
@limiter.limit("10/minute")
async def get_threshold(request: Request, market: str = "SP500"):
    from src.data import fetch_data
    from src.features import FeatureBuilder, FEATURE_CATALOG
    from src.tickers import MARKET_TICKERS
    from datetime import datetime, timedelta
    import pandas as pd

    cached = r.get(f"threshold:{market}")
    if cached:
        return json.loads(cached)

    today = datetime.now().strftime("%Y-%m-%d")
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    tickers = MARKET_TICKERS[market][:50]

    data = fetch_data(tickers=tickers, start=one_year_ago, end=today)
    builder = FeatureBuilder(data)
    all_features = list(FEATURE_CATALOG.keys())
    df = builder.build_custom({"R": all_features, "G": all_features, "B": all_features})

    returns = df.groupby("Ticker")["Close"].pct_change(5).shift(-5).dropna()
    lo = round(float(returns.quantile(0.70)), 3)
    hi = round(float(returns.quantile(0.80)), 3)
    lo = max(lo, 0.005)
    mid = round((lo + hi) / 2, 3)


    result = {
        "market": market,
        "threshold_lo": lo,
        "threshold_hi": hi,
        "future_days": 5,
        "label": f"around %{int(mid*100)} increase"
    }

    r.setex(f"threshold:{market}", CACHE_TTL, json.dumps(result))
    return result
    
@app.get("/model/history/{market}", tags=["Monitoring"])
@limiter.limit("10/minute")
async def get_model_history(request: Request, market: str):
    try:
        import mlflow
        from config import MLFLOW_TRACKING_URI
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        
        experiment = mlflow.get_experiment_by_name(market)
        if experiment is None:
            return []
        
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=20,
        )
        
        result = []
        for _, run in runs.iterrows():
            result.append({
                "date":     run.get("start_time", "").isoformat() if hasattr(run.get("start_time", ""), "isoformat") else str(run.get("start_time", "")),
                "f1_macro": run.get("metrics.f1_macro"),
                "accuracy": run.get("metrics.accuracy"),
                "name":     run.get("tags.mlflow.runName", ""),
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gradcam/{ticker}", tags=["Visualisation"])
@limiter.limit("20/minute")
async def get_gradcam(request: Request, ticker: str, market: str = "SP500"):
    try:
        pred = predictors.get(market)
        if pred is None:
            raise HTTPException(status_code=404, detail=f"No model for market: {market}")
        
        cached = get_cached_gradcam(market, ticker.upper())
        if cached:
            return Response(content=cached, media_type="image/png")
        
        png = pred.gradcam_png(ticker.upper())
        set_cached_gradcam(market, ticker.upper(), png)
        return Response(content=png, media_type="image/png")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/weights", tags=["Visualisation"])
@limiter.limit("20/minute")
async def get_weights(request: Request, market: str = "SP500"):
    try:
        pred = predictors.get(market)
        if pred is None:
            raise HTTPException(status_code=404, detail=f"No model for market: {market}")
        return Response(content=pred.weights_png(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/weights_json", tags=["Visualisation"])
@limiter.limit("20/minute")
async def get_weights_json(request: Request, market: str = "SP500"):
    try:
        pred = predictors.get(market)
        if pred is None:
            raise HTTPException(status_code=404, detail=f"No model for market: {market}")
        weights      = pred.model.layers[1].layer.layer.get_weights()[0]
        feature_cols = pred.meta["feature_cols"]
        result = {}
        for i, name in enumerate(feature_cols):
            if i < weights.shape[0]:
                result[name] = {
                    "R": round(float(weights[i, 0]), 4),
                    "G": round(float(weights[i, 1]), 4),
                    "B": round(float(weights[i, 2]), 4),
                }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    loaded = list(predictors.keys())
    if not loaded:
        return HealthResponse(status="no_model", model_loaded=False,
                              tickers=[], window_size=0, future_days=0, f1_macro=None)
    pred = next(iter(predictors.values()))
    return HealthResponse(
        status="ok",
        model_loaded=True,
        tickers=pred.meta.get("tickers", []),
        window_size=pred.meta.get("window_size", 0),
        future_days=pred.meta.get("future_days", 0),
        f1_macro=pred.meta.get("f1_macro"),
    )


def _run_training(job_id: str, req: TrainRequest):
    global predictors
    try:
        from src.tickers import MARKET_TICKERS
        tickers      = req.tickers if req.tickers else MARKET_TICKERS.get(req.market, [])
        cfg          = ExperimentConfig(
            tickers=tickers, start_date=req.start_date, end_date=req.end_date,
            window_size=req.window_size, stride=req.stride, future_days=req.future_days,
        )
        data         = fetch_data(tickers=cfg.tickers, start=cfg.start_date, end=cfg.end_date)
        builder      = FeatureBuilder(data)
        feature_cols = list(FEATURE_CATALOG.keys())
        eb           = ExperimentBuilder()

        import mlflow
        from config import MLFLOW_TRACKING_URI
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(req.market)

        exp = eb.build_experiment(
            name=req.name, window_size=cfg.window_size, feature_cols=feature_cols,
            future_days=cfg.future_days, stride=cfg.stride, builder=builder,
            tickers=cfg.tickers, cfg=cfg,
        )
        exp.prepare_data()
        
        if req.fine_tune and os.path.exists("saved_model_global"):
            exp.fine_tune(base_model_path="saved_model_global")
        else:
            exp.train()
        
        exp.evaluate()
        
        save_path = "saved_model_global" if req.name == "global_model" else f"saved_model_{req.market.lower()}"
        exp.save(save_path)
        
        from api.cache import invalidate_cache
        invalidate_cache(req.market)
        
        predictors[req.market] = Predictor(model_path=save_path)

        train_status[job_id] = {
            "status":   "done",
            "market":   req.market,
            "accuracy": round(exp.accuracy, 4),
            "f1_macro": round(exp.f1_macro, 4),
        }
    except Exception as e:
        train_status[job_id] = {"status": "error", "detail": str(e)}

@app.post("/train", tags=["Training"])
@limiter.limit("3/minute")
async def train_model(request: Request,req: TrainRequest, background_tasks: BackgroundTasks):
    job_id = f"train_{int(time.time())}"
    train_status[job_id] = {"status": "running"}
    background_tasks.add_task(_run_training, job_id, req)
    return {"job_id": job_id, "status": "started"}


@app.get("/train/{job_id}", tags=["Training"])
def get_train_status(job_id: str):
    if job_id not in train_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return train_status[job_id]

@app.post("/predictions/save", tags=["Monitoring"])
@limiter.limit("5/minute")
async def save_predictions(request: Request, market: str, callback_url: str = "http://178.104.125.39:5175/api/predictions"):
    try:
        pred    = predictors.get(market)
        if pred is None:
            raise HTTPException(status_code=404, detail=f"No model for market: {market}")
        results = pred.predict_all()
        
        import requests
        from datetime import datetime, timedelta
        
        today       = datetime.now().date()
        target_date = today + timedelta(days=pred.meta["future_days"])
        
        payload = [{
            "ticker":          r["ticker"],
            "market":          market,
            "signal":          r["signal"],
            "confidence":      r["confidence"],
            "price_at_signal": r["last_price"] or 0,
            "predicted_date":  str(today),
            "target_date":     str(target_date),
        } for r in results if r["signal"] != "ERROR"]

        requests.post(callback_url, json=payload, timeout=10)
        return {"saved": len(payload)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))