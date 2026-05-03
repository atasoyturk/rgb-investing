import numpy as np
import pandas as pd
import pandas_ta as ta
from config import LOG_RETURN_CLIP, VOLATILITY_CLIP, VOLUME_CLIP

FEATURE_CATALOG = {
    # --- RAW ---
    "log_return":      {"desc": "Log Return          (raw price movement)",   "category": "RAW"},
    "volatility":      {"desc": "Volatility          (High-Low / Close)",     "category": "RAW"},
    "volume_ratio":    {"desc": "Volume Ratio        (volume anomaly)",        "category": "RAW"},
    # --- MOMENTUM ---
    "rsi_14":          {"desc": "RSI(14)             (momentum oscillator)",   "category": "MOMENTUM"},
    "stoch":           {"desc": "Stochastic(14)      (momentum oscillator)",   "category": "MOMENTUM"},
    "mfi":             {"desc": "MFI(14)             (money flow index)",      "category": "MOMENTUM"},
    "cci":             {"desc": "CCI(14)             (commodity channel idx)", "category": "MOMENTUM"},
    "roc":             {"desc": "ROC(10)             (rate of change)",        "category": "MOMENTUM"},
    # --- TREND ---
    "macd":            {"desc": "MACD(12,26)         (trend strength)",        "category": "TREND"},
    "macd_signal":     {"desc": "MACD Signal         (trend signal)",          "category": "TREND"},
    "adx":             {"desc": "ADX(14)             (trend strength 0-100)",  "category": "TREND"},
    "vwap_ratio":      {"desc": "Close/VWAP          (institutional ref)",     "category": "TREND"},
    # --- VOLATILITY ---
    "bb_pct":          {"desc": "BB %B(20)           (band position)",         "category": "VOLATILITY"},
    "bb_width":        {"desc": "BB Width(20)        (volatility range)",      "category": "VOLATILITY"},
    "atr":             {"desc": "ATR(14)             (true range volatility)", "category": "VOLATILITY"},
    # --- VOLUME ---
    "obv_ratio":       {"desc": "OBV Ratio           (volume trend)",          "category": "VOLUME"},
}


def compute_feature(df: pd.DataFrame, feat: str) -> pd.Series:
    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    volume = df["Volume"]

    if feat == "log_return":
        s = np.log(close / close.shift(1))
        s = s.clip(-LOG_RETURN_CLIP, LOG_RETURN_CLIP)
        s = (s + LOG_RETURN_CLIP) / (2 * LOG_RETURN_CLIP)

    elif feat == "volatility":
        s = (high - low) / close.shift(1)
        s = s.clip(0, VOLATILITY_CLIP) / VOLATILITY_CLIP

    elif feat == "volume_ratio":
        ma20 = volume.rolling(20).mean()
        s = np.log(volume / ma20)
        s = s.clip(-VOLUME_CLIP, VOLUME_CLIP)
        s = (s + VOLUME_CLIP) / (2 * VOLUME_CLIP)

    elif feat == "rsi_14":
        s = ta.rsi(close, length=14) / 100

    elif feat == "stoch":
        s = ta.stoch(high, low, close, k=14)
        s = s["STOCHk_14_3_3"] / 100 if s is not None else pd.Series(np.nan, index=close.index)

    elif feat == "mfi":
        s = ta.mfi(high, low, close, volume, length=14)
        s = s / 100 if s is not None else pd.Series(np.nan, index=close.index)

    elif feat == "cci":
        s = ta.cci(high, low, close, length=14)
        if s is not None:
            s = (s.clip(-200, 200) + 200) / 400
        else:
            s = pd.Series(np.nan, index=close.index)

    elif feat == "roc":
        s = ta.roc(close, length=10)
        if s is not None:
            s = (s.clip(-20, 20) + 20) / 40
        else:
            s = pd.Series(np.nan, index=close.index)

    elif feat == "macd":
        m = ta.macd(close, fast=12, slow=26, signal=9)
        s = m["MACD_12_26_9"] if m is not None else pd.Series(np.nan, index=close.index)

    elif feat == "macd_signal":
        m = ta.macd(close, fast=12, slow=26, signal=9)
        s = m["MACDs_12_26_9"] if m is not None else pd.Series(np.nan, index=close.index)

    elif feat == "adx":
        result = ta.adx(high, low, close, length=14)
        s = result["ADX_14"] / 100 if result is not None else pd.Series(np.nan, index=close.index)

    elif feat == "vwap_ratio":
        vwap = (close * volume).rolling(20).sum() / volume.rolling(20).sum()
        s = (close / vwap).clip(0.8, 1.2)
        s = (s - 0.8) / 0.4

    elif feat == "bb_pct":
        bb = ta.bbands(close, length=20)
        s = bb["BBP_20_2.0_2.0"].clip(0, 1) if bb is not None else pd.Series(np.nan, index=close.index)

    elif feat == "bb_width":
        bb = ta.bbands(close, length=20)
        if bb is None:
            s = pd.Series(np.nan, index=close.index)
        else:
            s = (bb["BBU_20_2.0_2.0"] - bb["BBL_20_2.0_2.0"]) / bb["BBM_20_2.0_2.0"]

    elif feat == "atr":
        result = ta.atr(high, low, close, length=14)
        if result is not None:
            atr_pct = result / close
            s = atr_pct.clip(0, 0.1) / 0.1
        else:
            s = pd.Series(np.nan, index=close.index)

    elif feat == "obv_ratio":
        obv = ta.obv(close, volume)
        if obv is not None:
            obv_ma = obv.rolling(20).mean()
            ratio  = obv / (obv_ma.abs() + 1e-8)
            s = ratio.clip(-3, 3)
            s = (s + 3) / 6
        else:
            s = pd.Series(np.nan, index=close.index)

    else:
        raise ValueError(f"Unknown feature: {feat}")

    s.name = feat
    return s


class FeatureBuilder:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def build_custom(self, channel_plan: dict) -> pd.DataFrame:
        if hasattr(self.data.index, "tz") and self.data.index.tz is not None:
            self.data = self.data.copy()
            self.data.index = self.data.index.tz_convert(None)

        all_features = list(dict.fromkeys(
            feat for feats in channel_plan.values() for feat in feats
        ))

        result_parts = []
        for ticker in self.data["Ticker"].unique():
            tdf = self.data[self.data["Ticker"] == ticker].copy()
            computed = {feat: compute_feature(tdf, feat).values for feat in all_features}
            out = pd.DataFrame(computed, index=tdf.index)
            out["Close"]  = tdf["Close"].values
            out["Ticker"] = ticker
            result_parts.append(out)

        df = pd.concat(result_parts).dropna().copy()
        print(f"[FeatureBuilder] Shape: {df.shape}")
        return df