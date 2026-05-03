import pandas as pd
import numpy as np

from config import STRIDE, FUTURE_DAYS
from src.features import FeatureBuilder, FEATURE_CATALOG
from src.normalization import QuantileScaler
from src.experiment import RGBExperiment
from src.experiment_config import ExperimentConfig


def _apply_scaler(df, feature_cols, tickers, train_split) -> tuple[pd.DataFrame, QuantileScaler]:
    train_parts, test_parts = [], []

    for ticker in tickers:
        tdf = df[df["Ticker"] == ticker]
        split_idx = int(len(tdf) * train_split)
        train_parts.append(tdf.iloc[:split_idx])
        test_parts.append(tdf.iloc[split_idx:])

    train_df = pd.concat(train_parts)
    test_df  = pd.concat(test_parts)

    scaler = QuantileScaler()
    scaler.fit(train_df, feature_cols)
    train_df = scaler.transform(train_df).copy()
    test_df  = scaler.transform(test_df).copy()

    train_df["_split"] = "train"
    test_df["_split"]  = "test"

    scaled_df = pd.concat([train_df, test_df]).sort_index()

    bounded  = [f for f in feature_cols if f not in scaler.stats]
    rescaled = list(scaler.stats.keys())
    print(
        f"[Scaler] train={len(train_df):,}  test={len(test_df):,} | "
        f"quantile-rescaled: {rescaled} | "
        f"already-bounded (skipped): {bounded}"
    )
    return scaled_df, scaler


class ExperimentBuilder:

    def __init__(self):
        self.keys = list(FEATURE_CATALOG.keys())

    def build_experiment(self, name, window_size, feature_cols,
                         future_days, stride, builder, tickers,
                         cfg: ExperimentConfig) -> RGBExperiment:
        build_plan        = {"R": feature_cols, "G": feature_cols, "B": feature_cols}
        df                = builder.build_custom(build_plan)
        scaled_df, scaler = _apply_scaler(df, feature_cols, tickers, cfg.train_split)

        return RGBExperiment(
            name=name,
            df=scaled_df,
            scaler=scaler,
            feature_cols=feature_cols,
            window_size=window_size,
            future_days=future_days,
            stride=stride,
        )