"""
experiment.py
-------------
RGBExperiment: orchestrates dataset creation, training, evaluation,
and visualisation for a single projection-mode experiment.
"""

import json
import os

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import keras
import mlflow
import mlflow.keras

from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (
    confusion_matrix, classification_report, accuracy_score,
    precision_score, recall_score, f1_score,
)

from src.dataset import create_dataset
from src.model import build_model
from src.normalization import QuantileScaler
from config import (
    EPOCHS, BATCH_SIZE, LABEL_THRESHOLD, PATIENCE, CLASS_WEIGHT_MULTIPLIER,
    MLFLOW_EXPERIMENT_NAME, MLFLOW_TRACKING_URI, FUTURE_DAYS,
)


class RGBExperiment:

    def __init__(
        self,
        name: str,
        df,
        feature_cols: list,
        scaler: QuantileScaler | None = None,
        window_size: int = 400,
        stride: int = 5,
        future_days: int | None = None,
        label_threshold: float | None = None,  # YENİ

    ):
        self.name         = name
        self.df           = df
        self.feature_cols = feature_cols
        self.scaler       = scaler          # fitted QuantileScaler from builder
        self.window_size  = window_size
        self.stride       = stride
        self.future_days  = future_days if future_days is not None else FUTURE_DAYS
        self.label_threshold = label_threshold if label_threshold is not None else LABEL_THRESHOLD
        self.image_size   = int(np.sqrt(window_size))

        self.X_train = self.X_test = None
        self.y_train = self.y_test = None
        self.class_weight = None
        self.baseline     = None

        self.model   = None
        self.history = None

        self.y_pred         = None
        self.y_pred_classes = None
        self.accuracy       = None
        self.f1_macro       = None
        self._mlflow_run_id = None

    # ----------------------------------------------------------
    # Data preparation
    # ----------------------------------------------------------

    def prepare_data(self):
        tickers = list(self.df["Ticker"].unique())

        self.X_train, self.X_test, self.y_train, self.y_test = create_dataset(
            df=self.df,
            feature_cols=self.feature_cols,
            window_size=self.window_size,
            stride=self.stride,
            tickers=tickers,
            future_days=self.future_days,
            label_threshold=self.label_threshold,  # YENİ
        )

        print(
            f"[{self.name}] Data ready → "
            f"Train: {self.X_train.shape[0]:,}  "
            f"Test: {self.X_test.shape[0]:,}  "
            f"Image: {self.X_train.shape[1]}x{self.X_train.shape[2]}x{self.X_train.shape[3]}"
        )

        weights = compute_class_weight(
            class_weight="balanced",
            classes=np.array([0, 1]),
            y=self.y_train,
        )
        self.class_weight = {
            0: float(weights[0]),
            1: float(weights[1]) * CLASS_WEIGHT_MULTIPLIER,
        }
        print(f"  Class weights : {self.class_weight}")

        self.baseline = float(self.y_test.mean())
        print(f"  Baseline (always BUY): {self.baseline:.2%}")

    # ----------------------------------------------------------
    # Training
    # ----------------------------------------------------------

    def train(self):
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

        with mlflow.start_run(run_name=self.name):
            mlflow.log_params({
                "experiment_name": self.name,
                "feature_cols":    str(self.feature_cols),
                "n_features":      len(self.feature_cols),
                "window_size":     self.window_size,
                "image_size":      self.image_size,
                "batch_size":      BATCH_SIZE,
                "epochs":          EPOCHS,
                "patience":        PATIENCE,
                "class_weight_0":  round(self.class_weight[0], 3),
                "class_weight_1":  round(self.class_weight[1], 3),
                "future_days":     self.future_days,
                "stride":          self.stride,
            })

            n_features = self.X_train.shape[-1]
            self.model = build_model(image_size=self.image_size, n_features=n_features)

            early_stop = keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=PATIENCE,
                restore_best_weights=True,
            )

            self.history = self.model.fit(
                self.X_train, self.y_train,
                epochs=EPOCHS,
                batch_size=BATCH_SIZE,
                validation_data=(self.X_test, self.y_test),
                class_weight=self.class_weight,
                shuffle=False,
                verbose=0,
                callbacks=[early_stop],
            )

            for epoch, (loss, val_loss) in enumerate(zip(
                self.history.history["loss"],
                self.history.history["val_loss"],
            )):
                mlflow.log_metric("train_loss", loss,     step=epoch)
                mlflow.log_metric("val_loss",   val_loss, step=epoch)

            mlflow.log_metric("total_epochs",  len(self.history.history["loss"]))
            mlflow.log_metric("best_val_loss", min(self.history.history["val_loss"]))
            mlflow.log_metric("baseline",      self.baseline)
            mlflow.keras.log_model(self.model, "model")
            self._mlflow_run_id = mlflow.active_run().info.run_id

    # ----------------------------------------------------------
    # Evaluation
    # ----------------------------------------------------------

    def evaluate(self):
        self.y_pred         = self.model.predict(self.X_test, verbose=0)
        self.y_pred_classes = (self.y_pred > 0.5).astype(int).flatten()
        self.accuracy       = accuracy_score(self.y_test, self.y_pred_classes)
        self.f1_macro       = f1_score(
            self.y_test, self.y_pred_classes, average="macro", zero_division=0
        )

        print("\n" + classification_report(
            self.y_test, self.y_pred_classes,
            target_names=["Decrease (0)", "Increase (1)"],
            zero_division=0,
        ))

        if self._mlflow_run_id:
            with mlflow.start_run(run_id=self._mlflow_run_id):
                mlflow.log_metrics({
                    "accuracy":           round(self.accuracy, 4),
                    "f1_macro":           round(self.f1_macro, 4),
                    "baseline_beaten":    int(self.accuracy > self.baseline),
                    "precision_decrease": round(precision_score(self.y_test, self.y_pred_classes, pos_label=0, zero_division=0), 4),
                    "recall_decrease":    round(recall_score   (self.y_test, self.y_pred_classes, pos_label=0, zero_division=0), 4),
                    "precision_increase": round(precision_score(self.y_test, self.y_pred_classes, pos_label=1, zero_division=0), 4),
                    "recall_increase":    round(recall_score   (self.y_test, self.y_pred_classes, pos_label=1, zero_division=0), 4),
                    "f1_increase":        round(f1_score       (self.y_test, self.y_pred_classes, pos_label=1, zero_division=0), 4),
                })

    # ----------------------------------------------------------
    # Projection weights
    # ----------------------------------------------------------

    def print_projection_weights(self):
        try:
            weights = self.model.layers[1].layer.layer.get_weights()[0]
        except Exception:
            print("Could not extract projection weights.")
            return

        print("\n" + "=" * 55)
        print(f"{'Feature':<22} {'R':>8} {'G':>8} {'B':>8}")
        print("-" * 55)
        for i, name in enumerate(self.feature_cols):
            if i < weights.shape[0]:
                print(f"{name:<22} {weights[i,0]:>+8.3f} {weights[i,1]:>+8.3f} {weights[i,2]:>+8.3f}")
        print("=" * 55)
        
    def fine_tune(self, base_model_path: str, epochs: int = 10):
        
        import tensorflow as tf
        
        # Global modeli yükle
        self.model = tf.keras.models.load_model(
            os.path.join(base_model_path, "model.keras")
        )
        
        # Tüm katmanları dondur
        for layer in self.model.layers:
            layer.trainable = False
        
        # Sadece projection (layers[1]) ve output (layers[-1]) aç
        self.model.layers[1].trainable = True   # TimeDistributed projection
        self.model.layers[-1].trainable = True  # Dense(1) sigmoid
        
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
            loss="binary_crossentropy",
            metrics=["accuracy"],
        )
        
        print(f"[{self.name}] Fine-tuning from: {base_model_path}")
        trainable = sum(tf.size(w).numpy() for w in self.model.trainable_weights)
        print(f"  Trainable params: {trainable:,}")
        
        early_stop = keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True,
        )
        
        self.history = self.model.fit(
            self.X_train, self.y_train,
            epochs=epochs,
            batch_size=BATCH_SIZE,
            validation_data=(self.X_test, self.y_test),
            class_weight=self.class_weight,
            shuffle=False,
            verbose=1,
            callbacks=[early_stop],
        )

    # ----------------------------------------------------------
    # Save
    # ----------------------------------------------------------

    def save(self, path: str = "saved_model"):
        """
        Persists model, scaler stats, and metadata.
        Uses the scaler fitted in builder.py — no re-fitting required.
        """
        os.makedirs(path, exist_ok=True)

        # 1. Model weights
        self.model.save(os.path.join(path, "model.keras"))

        # 2. Scaler stats
        if self.scaler is not None:
            scaler_data = {f: list(stats) for f, stats in self.scaler.stats.items()}
        else:
            # Fallback: re-fit if scaler was not passed (e.g. grad_cam.py usage)
            from config import TRAIN_SPLIT
            import pandas as pd
            scaler = QuantileScaler()
            train_parts = []
            for ticker in self.df["Ticker"].unique():
                tdf = self.df[self.df["Ticker"] == ticker]
                train_parts.append(tdf.iloc[: int(len(tdf) * TRAIN_SPLIT)])
            scaler.fit(pd.concat(train_parts), self.feature_cols)
            scaler_data = {f: list(stats) for f, stats in scaler.stats.items()}

        with open(os.path.join(path, "scaler.json"), "w") as f:
            json.dump(scaler_data, f, indent=2)

        # 3. Metadata
        tickers = list(self.df["Ticker"].unique())
        meta = {
            "feature_cols": self.feature_cols,
            "window_size":  self.window_size,
            "future_days":  self.future_days,
            "stride":       self.stride,
            "image_size":   self.image_size,
            "tickers":      tickers,
            "accuracy":     round(self.accuracy, 4) if self.accuracy is not None else None,
            "f1_macro":     round(self.f1_macro, 4) if self.f1_macro is not None else None,
            "baseline":     round(self.baseline, 4) if self.baseline is not None else None,
        }
        with open(os.path.join(path, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

        print(f"\n[Save] Model saved to '{path}/'")
        print(f"  model.keras")
        print(f"  scaler.json  ({len(scaler_data)} features scaled)")
        print(f"  meta.json    (window={self.window_size}, future={self.future_days})")

    # ----------------------------------------------------------
    # Visualisation
    # ----------------------------------------------------------

    def plot_confusion_matrix(self, ax=None):
        cm   = confusion_matrix(self.y_test, self.y_pred_classes)
        show = ax is None
        if ax is None:
            _, ax = plt.subplots(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                    xticklabels=["Decrease", "Increase"],
                    yticklabels=["Decrease", "Increase"], ax=ax)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(f"{self.name}\nAcc: {self.accuracy:.2%}  Base: {self.baseline:.2%}")
        if show:
            plt.tight_layout(); plt.show()

    def plot_loss(self, ax=None):
        show = ax is None
        if ax is None:
            _, ax = plt.subplots(figsize=(6, 4))
        ax.plot(self.history.history["loss"],     label="Train Loss")
        ax.plot(self.history.history["val_loss"], label="Val Loss")
        ax.set_title(f"{self.name} - Loss")
        ax.legend()
        if show:
            plt.tight_layout(); plt.show()

    def plot_sample_images(self):
        fig, axes = plt.subplots(1, 2, figsize=(8, 4))
        buy_idx  = np.where(self.y_train == 1)[0][0]
        sell_idx = np.where(self.y_train == 0)[0][0]
        axes[0].imshow(self.X_train[buy_idx].mean(axis=-1),  cmap="viridis")
        axes[0].set_title("BUY",  color="green", fontsize=13); axes[0].axis("off")
        axes[1].imshow(self.X_train[sell_idx].mean(axis=-1), cmap="viridis")
        axes[1].set_title("SELL", color="red",   fontsize=13); axes[1].axis("off")
        plt.suptitle(f"Mean Feature Map: {self.name}", fontsize=14)
        plt.tight_layout(); plt.show()
