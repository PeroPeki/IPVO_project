"""
ML Model Trening – Dynamic Pricing
Train/test split 80/20, metrika RMSE, sprema bolji model u /app/models/.
"""

import os
import math
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from pymongo import MongoClient
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split


def load_training_data():
    client = MongoClient("mongodb://mongo:27017")
    db = client["mydb"]
    records = list(db.ml_training_data.find({}, {"_id": 0}))
    client.close()
    if not records:
        raise ValueError(
            "Nema training podataka! Pokrenite generate_training_data.py prvo."
        )
    return pd.DataFrame(records)


def prepare_features(df):
    df = df.copy()
    df["log_listeners"] = df["artist_listeners"].apply(lambda x: math.log10(x + 1))
    df["log_playcount"] = df["artist_playcount"].apply(lambda x: math.log10(x + 1))

    feature_cols = [
        "log_listeners", "log_playcount", "genre_encoded",
        "venue_capacity", "days_until_event", "tickets_sold_ratio", "day_of_week",
    ]
    return df[feature_cols], df["optimal_price"], feature_cols


def train_and_evaluate():
    df = load_training_data()
    X, y, feature_cols = prepare_features(df)

    print(
        f"Dataset: {len(X)} zapisa | Cijena: min={y.min():.2f} EUR, "
        f"max={y.max():.2f} EUR, avg={y.mean():.2f} EUR"
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    # Random Forest
    rf = RandomForestRegressor(
        n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
    )
    rf.fit(X_train, y_train)
    rf_rmse = math.sqrt(mean_squared_error(y_test, rf.predict(X_test)))
    print(f"Random Forest RMSE: {rf_rmse:.4f} EUR")

    # XGBoost
    xgb_model = xgb.XGBRegressor(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1,
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    xgb_rmse = math.sqrt(mean_squared_error(y_test, xgb_model.predict(X_test)))
    print(f"XGBoost RMSE: {xgb_rmse:.4f} EUR")

    if xgb_rmse < rf_rmse:
        best_model, best_name, best_rmse = xgb_model, "XGBoost", xgb_rmse
    else:
        best_model, best_name, best_rmse = rf, "RandomForest", rf_rmse

    print(f"\nPobjednički model: {best_name} (RMSE: {best_rmse:.4f} EUR)")

    os.makedirs("/app/models", exist_ok=True)
    joblib.dump(best_model, "/app/models/pricing_model.pkl")
    joblib.dump(feature_cols, "/app/models/feature_cols.pkl")

    client = MongoClient("mongodb://mongo:27017")
    client["mydb"].model_metadata.insert_one({
        "trained_at": datetime.utcnow(),
        "best_model": best_name,
        "best_rmse": best_rmse,
        "rf_rmse": rf_rmse,
        "xgb_rmse": xgb_rmse,
        "train_size": len(X_train),
        "features": feature_cols,
    })
    client.close()
    print("Model i metadata spremljeni.")


if __name__ == "__main__":
    train_and_evaluate()
