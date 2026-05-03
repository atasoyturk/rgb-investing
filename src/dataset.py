import numpy as np
from config import FUTURE_DAYS, LABEL_THRESHOLD


def create_dataset(
    df,
    feature_cols: list,
    window_size: int,
    stride: int,
    tickers: list,
    future_days: int = FUTURE_DAYS,
    label_threshold: float = LABEL_THRESHOLD,
):
    
    h = int(np.sqrt(window_size))
    n = len(feature_cols)
    X_train, X_test, y_train, y_test = [], [], [], []

    for ticker in tickers:
        tdf = df[df["Ticker"] == ticker].copy()
        if len(tdf) < window_size + future_days:
            print(f"  [dataset] {ticker}: too few rows, skipping.")
            continue

        features    = tdf[feature_cols].values
        close       = tdf["Close"].values
        split_flags = tdf["_split"].values

        for i in range(0, len(features) - window_size - future_days, stride):
            window = features[i : i + window_size]
            image  = window.reshape(h, h, n)

            today_close = close[i + window_size - 1]
            future_mean = close[i + window_size : i + window_size + future_days].mean()
            return_pct  = (future_mean - today_close) / today_close
            label       = 1 if return_pct > label_threshold else 0

            if split_flags[i + window_size - 1] == "train":
                X_train.append(image)
                y_train.append(label)
            else:
                X_test.append(image)
                y_test.append(label)

    return (
        np.array(X_train, dtype=np.float32),
        np.array(X_test,  dtype=np.float32),
        np.array(y_train, dtype=np.int32),
        np.array(y_test,  dtype=np.int32),
    )
