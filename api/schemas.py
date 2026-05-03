from pydantic import BaseModel
from typing import Optional

class TrainRequest(BaseModel):
    name: str
    market: str  # SP500, NASDAQ100, BIST100
    tickers: list[str]
    start_date: str
    end_date: str
    window_size: int = 400
    stride: int
    future_days: int
    tickers: list[str] = []  
    fine_tune: bool = False


class SignalResponse(BaseModel):
    ticker: str
    signal: str
    confidence: float
    last_price: Optional[float]
    currency: str = "$"
    future_days: int
    in_training_set: bool


class SignalsTableResponse(BaseModel):
    signals: list[SignalResponse]
    model_f1: Optional[float]
    model_accuracy: Optional[float]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    tickers: list[str]
    window_size: int
    future_days: int
    f1_macro: Optional[float]
