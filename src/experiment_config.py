from dataclasses import dataclass, field
from config import (
    WINDOW_SIZE, STRIDE, FUTURE_DAYS,
    LABEL_THRESHOLD, TRAIN_SPLIT,
)

@dataclass
class ExperimentConfig:
    tickers:         list[str] = field(default_factory=list)
    start_date:      str       = "2016-05-01"
    end_date:        str       = "2026-05-01"
    window_size:     int       = WINDOW_SIZE
    stride:          int       = STRIDE
    future_days:     int       = FUTURE_DAYS
    label_threshold: float     = LABEL_THRESHOLD
    train_split:     float     = TRAIN_SPLIT