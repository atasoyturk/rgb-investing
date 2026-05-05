"""
predictor.py
------------
Model loading, inference, Grad-CAM, and projection weight visualisation.
Instantiated once at API startup and kept in memory.
"""

import os, sys, json
from matplotlib import ticker
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tensorflow as tf
from io import BytesIO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data import fetch_data
from src.features import FeatureBuilder, FEATURE_CATALOG
from src.normalization import QuantileScaler

from datetime import datetime, timedelta



ALL_FEATURES = list(FEATURE_CATALOG.keys())


class Predictor:
    def __init__(self, model_path: str = "saved_model"):
        self.model_path   = model_path
        self.model        = None
        self.meta         = {}
        self.scaler_stats = {}
        self._load()

    def _load(self):
        keras_path  = os.path.join(self.model_path, "model.keras")
        meta_path   = os.path.join(self.model_path, "meta.json")
        scaler_path = os.path.join(self.model_path, "scaler.json")

        if not os.path.exists(keras_path):
            raise FileNotFoundError(
                f"Model not found: {keras_path}\nRun main.py first."
            )

        print(f"[Predictor] Loading model: {keras_path}")
        self.model = tf.keras.models.load_model(keras_path)

        with open(meta_path)   as f: self.meta         = json.load(f)
        with open(scaler_path) as f: self.scaler_stats = json.load(f)

        # Scaler bir kez init edilir, her predict'te yeniden oluşturulmaz
        self.scaler = QuantileScaler()
        self.scaler.stats = {f: tuple(v) for f, v in self.scaler_stats.items()}

        print(
            f"[Predictor] Ready — "
            f"window={self.meta['window_size']}  "
            f"future={self.meta['future_days']}  "
            f"f1={self.meta.get('f1_macro', 'N/A')}"
        )

    def _fetch_and_prepare(self, ticker: str) -> tuple[np.ndarray, float]:
        window_size  = self.meta["window_size"]
        feature_cols = self.meta["feature_cols"]
        image_size   = self.meta["image_size"]
        n_features   = len(feature_cols)

        start = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
        end   = datetime.now().strftime("%Y-%m-%d")

        data = fetch_data(tickers=[ticker], start=start, end=end)
        if data.empty:
            raise ValueError(f"No data for '{ticker}'.")

        data = data.copy()

        if hasattr(data.index, "tz") and data.index.tz is not None:
            data.index = data.index.tz_convert(None)
        if "Ticker" not in data.columns:
            data["Ticker"] = ticker

        builder = FeatureBuilder(data)
        df      = builder.build_custom({"R": feature_cols, "G": feature_cols, "B": feature_cols})
        tdf     = df[df["Ticker"] == ticker].copy()

        if len(tdf) < window_size:
            raise ValueError(f"Not enough data for '{ticker}': need {window_size}, got {len(tdf)}.")

        tdf        = self.scaler.transform(tdf)
        tdf        = tdf.tail(window_size)
        last_price = float(tdf["Close"].iloc[-1])
        image      = tdf[feature_cols].values.reshape(image_size, image_size, n_features).astype(np.float32)
        return image, last_price

    def _prepare_ticker(self, tdf: pd.DataFrame, ticker: str) -> tuple[np.ndarray, float]:
        window_size  = self.meta["window_size"]
        feature_cols = self.meta["feature_cols"]
        image_size   = self.meta["image_size"]
        n_features   = len(feature_cols)

        if hasattr(tdf.index, "tz") and tdf.index.tz is not None:
            tdf.index = tdf.index.tz_convert(None)
        if "Ticker" not in tdf.columns:
            tdf["Ticker"] = ticker

        builder = FeatureBuilder(tdf)
        df      = builder.build_custom({"R": feature_cols, "G": feature_cols, "B": feature_cols})
        tdf     = df[df["Ticker"] == ticker].copy()

        if len(tdf) < window_size:
            raise ValueError(f"Not enough data: need {window_size}, got {len(tdf)}")

        tdf        = self.scaler.transform(tdf)
        tdf        = tdf.tail(window_size)
        last_price = float(tdf["Close"].iloc[-1])
        image      = tdf[feature_cols].values.reshape(image_size, image_size, n_features).astype(np.float32)
        return image, last_price

    def predict(self, ticker: str) -> dict:
        image, last_price = self._fetch_and_prepare(ticker)
        prob              = float(self.model.predict(image[np.newaxis, ...], verbose=0)[0][0])
        signal            = "BUY" if prob > 0.5 else "SELL"
        confidence        = prob if prob > 0.5 else 1 - prob
        currency          = "₺" if ticker.endswith(".IS") else "$"
        return {
            "ticker":          ticker,
            "signal":          signal,
            "confidence":      round(confidence, 4),
            "last_price":      round(last_price, 2),
            "currency":        currency,
            "future_days":     self.meta["future_days"],
            "in_training_set": ticker in self.meta.get("tickers", []),
        }

    def predict_all(self) -> list[dict]:
        tickers = self.meta.get("tickers", [])
        start   = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
        end     = datetime.now().strftime("%Y-%m-%d")

        try:
            all_data = fetch_data(tickers=tickers, start=start, end=end)
        except Exception as e:
            print(f"[predict_all] fetch error: {e}")
            return []

        # 1. Tüm ticker'lar için image hazırla
        images      = []
        last_prices = []
        valid       = []
        errors      = []

        for t in tickers:
            try:
                tdf = all_data[all_data["Ticker"] == t].copy()
                if tdf.empty:
                    raise ValueError(f"No data for {t}")
                image, last_price = self._prepare_ticker(tdf, t)
                images.append(image)
                last_prices.append(last_price)
                valid.append(t)
            except Exception as e:
                print(f"  [{t}] prep error: {e}")
                errors.append(t)

        # 2. Tek seferde batch prediction
        results = []
        if images:
            batch = np.stack(images, axis=0)  # (N, 20, 20, 16)
            probs = self.model.predict(batch, batch_size=64, verbose=0).flatten()

            for t, prob, last_price in zip(valid, probs, last_prices):
                prob       = float(prob)
                signal     = "BUY" if prob > 0.5 else "SELL"
                confidence = prob if prob > 0.5 else 1 - prob
                currency   = "₺" if t.endswith(".IS") else "$"
                results.append({
                    "ticker":          t,
                    "signal":          signal,
                    "confidence":      round(confidence, 4),
                    "last_price":      round(last_price, 2),
                    "currency":        currency,
                    "future_days":     self.meta["future_days"],
                    "in_training_set": t in tickers,
                })

        # 3. Hatalı ticker'ları ekle
        for t in errors:
            results.append({
                "ticker":          t,
                "signal":          "ERROR",
                "confidence":      0.0,
                "last_price":      None,
                "currency":        "₺" if t.endswith(".IS") else "$",
                "future_days":     self.meta["future_days"],
                "in_training_set": True,
            })

        return results

    def gradcam_png(self, ticker: str) -> bytes:
        image, _ = self._fetch_and_prepare(ticker)
        last_conv = next(
            (l.name for l in reversed(self.model.layers) if isinstance(l, tf.keras.layers.Conv2D)),
            None,
        )
        if last_conv is None:
            raise ValueError("No Conv2D layer found.")

        grad_model = tf.keras.models.Model(
            inputs=self.model.inputs,
            outputs=[self.model.get_layer(last_conv).output, self.model.outputs],
        )
        img_tensor = tf.cast(image[np.newaxis, ...], tf.float32)
        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(img_tensor)
            loss = predictions[0][:, 0]
        grads        = tape.gradient(loss, conv_outputs)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        heatmap      = (conv_outputs[0] @ pooled_grads[..., tf.newaxis]).numpy().squeeze()
        heatmap      = np.maximum(heatmap, 0)
        if heatmap.max() > 0:
            heatmap /= heatmap.max()
        heatmap_resized = tf.image.resize(
            heatmap[..., np.newaxis], [image.shape[0], image.shape[1]]
        ).numpy().squeeze()

        prob     = float(predictions[0][0][0])
        signal   = "BUY" if prob > 0.5 else "SELL"
        color    = "green" if signal == "BUY" else "red"
        mean_img = image.mean(axis=-1)

        fig, axes = plt.subplots(1, 3, figsize=(12, 4))
        fig.suptitle(f"{ticker} — {signal} (confidence: {max(prob, 1-prob):.1%})", fontsize=13, color=color)
        axes[0].imshow(mean_img, cmap="viridis"); axes[0].set_title("Mean Feature Map"); axes[0].axis("off")
        axes[1].imshow(heatmap_resized, cmap="jet"); axes[1].set_title("Grad-CAM Heatmap"); axes[1].axis("off")
        mean_norm = (mean_img - mean_img.min()) / (mean_img.max() - mean_img.min() + 1e-8)
        overlay   = plt.cm.viridis(mean_norm)[:,:,:3] * 0.6 + plt.cm.jet(heatmap_resized)[:,:,:3] * 0.4
        axes[2].imshow(overlay); axes[2].set_title("Overlay"); axes[2].axis("off")
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        plt.close(fig); buf.seek(0)
        return buf.read()

    def weights_png(self) -> bytes:
        try:
            weights = self.model.layers[1].layer.layer.get_weights()[0]
        except Exception:
            raise ValueError("Could not extract projection weights.")

        feature_cols = self.meta["feature_cols"]
        n, x, width  = len(feature_cols), np.arange(len(feature_cols)), 0.25

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.bar(x - width, weights[:n, 0], width, label="R Channel", color="#E74C3C", alpha=0.8)
        ax.bar(x,         weights[:n, 1], width, label="G Channel", color="#2ECC71", alpha=0.8)
        ax.bar(x + width, weights[:n, 2], width, label="B Channel", color="#3498DB", alpha=0.8)
        ax.set_xticks(x); ax.set_xticklabels(feature_cols, rotation=45, ha="right", fontsize=10)
        ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
        ax.set_title("Learned projection weights — indicator → RGB channel", fontsize=13)
        ax.set_ylabel("Weight"); ax.legend(); ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        plt.close(fig); buf.seek(0)
        return buf.read()