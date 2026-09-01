import os
import sys
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def train_smooth_landslide_brain():
    print("[INFO] Generating Continuous Geotechnical Risk Surface for Kerala...")
    np.random.seed(42)
    n = 10000

    slope = np.random.uniform(0.5, 50.0, n)
    elevation = np.random.uniform(10.0, 2200.0, n)
    soil_type = np.random.choice([1, 2, 3], size=n, p=[0.4, 0.45, 0.15])
    rainfall = np.random.uniform(0.0, 350.0, n)
    saturation = np.random.uniform(15.0, 100.0, n)

    # Smooth multi-factor geotechnical risk model:
    # 1. Slope factor (0 to 1): gentle <10 deg has low risk, steep >35 deg has high risk
    slope_factor = np.clip((slope - 5.0) / 35.0, 0.0, 1.0) ** 1.35
    # 2. Rainfall factor (0 to 1): cumulative 72h rain
    rain_factor = np.clip((rainfall - 15.0) / 200.0, 0.0, 1.0) ** 1.15
    # 3. Saturation factor (0 to 1)
    sat_factor = np.clip((saturation - 35.0) / 55.0, 0.0, 1.0)
    # 4. Soil factor
    soil_factor = np.where(soil_type == 1, 1.15, np.where(soil_type == 2, 1.0, 0.65))

    # Continuous risk percentage (0 to 100)
    risk_pct = (slope_factor * 42.0 + rain_factor * 38.0 + sat_factor * 20.0) * soil_factor

    # Guard for low altitude coastal / flat water plains
    risk_pct = np.where((slope < 8.0) & (elevation < 120.0), risk_pct * 0.08, risk_pct)
    # Add mild natural geological variance
    noise = np.random.normal(0, 1.5, n)
    risk_pct = np.clip(risk_pct + noise, 0.5, 99.5)

    df = pd.DataFrame({
        'Slope_Angle': np.round(slope, 1),
        'Elevation': np.round(elevation, 1),
        'Soil_Type': soil_type,
        'Rainfall_72h': np.round(rainfall, 1),
        'Soil_Saturation': np.round(saturation, 1),
        'Landslide_Risk': np.round(risk_pct, 1)
    })

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(backend_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, "kerala_landslide_inventory.csv")
    df.to_csv(csv_path, index=False)

    X = df[['Slope_Angle', 'Elevation', 'Soil_Type', 'Rainfall_72h', 'Soil_Saturation']]
    y = df['Landslide_Risk']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("[INFO] Training Continuous Gradient Boosting Landslide Regressor...")
    model = GradientBoostingRegressor(
        n_estimators=160,
        learning_rate=0.07,
        max_depth=5,
        min_samples_split=6,
        min_samples_leaf=3,
        subsample=0.85,
        random_state=42
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    r2 = r2_score(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"[OK] Training Complete -> R2 Score: {r2:.4f} | RMSE: {rmse:.2f}%")

    models_dir = os.path.join(backend_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "landslide_model.pkl")
    joblib.dump(model, model_path)
    print(f"[OK] Saved continuous ML model to: {model_path}")

    # Inspect across gradient of conditions
    test_grid = pd.DataFrame([
        {'Slope_Angle': 4.0, 'Elevation': 30, 'Soil_Type': 3, 'Rainfall_72h': 15.0, 'Soil_Saturation': 35.0},
        {'Slope_Angle': 15.0, 'Elevation': 250, 'Soil_Type': 2, 'Rainfall_72h': 40.0, 'Soil_Saturation': 55.0},
        {'Slope_Angle': 25.0, 'Elevation': 550, 'Soil_Type': 2, 'Rainfall_72h': 85.0, 'Soil_Saturation': 70.0},
        {'Slope_Angle': 35.0, 'Elevation': 950, 'Soil_Type': 1, 'Rainfall_72h': 160.0, 'Soil_Saturation': 85.0},
        {'Slope_Angle': 45.0, 'Elevation': 1400, 'Soil_Type': 1, 'Rainfall_72h': 260.0, 'Soil_Saturation': 96.0}
    ])
    preds = model.predict(test_grid)
    labels = ["Lowland Coastal", "Gentle Foothill", "Midland Incline", "High Ghats Alert", "Extreme Torrent"]
    for lbl, p in zip(labels, preds):
        print(f"  -> {lbl:18s}: Continuous Risk = {p:.1f}%")

if __name__ == "__main__":
    train_smooth_landslide_brain()
