import pandas as pd


# Features that features.py already clips / maps to [0, 1].
# QuantileScaler skips these to avoid distorting their natural range.
#
# bb_width is NOT bounded (it's a ratio that can exceed 1), so it is
# intentionally absent here and will be scaled by QuantileScaler.
BOUNDED_FEATURES = frozenset({
    "log_return",
    "volatility",
    "volume_ratio",
    "rsi_14",
    "stoch",
    "mfi",
    "cci",
    "roc",
    "adx",
    "vwap_ratio",
    "bb_pct",
    "atr",
    "obv_ratio",
    # macd, macd_signal, bb_width → scaled below
})


class QuantileScaler:
   
    def __init__(self):
        self.stats: dict[str, tuple[float, float]] = {}

    def fit(self, df: pd.DataFrame, features: list[str]) -> "QuantileScaler":
        self.stats = {}
        for f in features:
            if f in BOUNDED_FEATURES:
                continue
            q01 = float(df[f].quantile(0.01))
            q99 = float(df[f].quantile(0.99))
            self.stats[f] = (q01, q99)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for f, (q01, q99) in self.stats.items():
            df[f] = ((df[f] - q01) / (q99 - q01 + 1e-8)).clip(0, 1)
        return df

    def fit_transform(self, df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
        return self.fit(df, features).transform(df)
