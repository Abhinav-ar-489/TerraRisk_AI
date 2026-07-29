import os
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

def generate_atmospheric_dataset(n_samples=2500):
    """
    Generates synthetic atmospheric telemetry for high-altitude Western Ghats.
    Models monsoonal depressions and convective precipitation triggers.
    """
    np.random.seed(42)
    
    # Feature distributions based on Kerala monsoonal records
    pressure = np.random.uniform(995.0, 1018.0, n_samples)  # hPa
    humidity = np.random.uniform(45.0, 99.0, n_samples)     # %
    temperature = np.random.uniform(18.0, 34.0, n_samples)  # Celsius
    
    # Orographic / Monsoonal precipitation modeling equation
    # Low pressure + high relative humidity = intense monsoon downpours
    pressure_delta = np.maximum(0, 1013.25 - pressure)
    saturation = (humidity / 100.0) ** 2.2
    
    # Non-linear rainfall depth output (mm/day)
    base_rain = (pressure_delta * 8.5) * saturation
    
    # Thermal convection multiplier
    convective_boost = np.where(temperature > 26.0, 1.2, 1.0)
    rainfall_mm = base_rain * convective_boost
    
    # Add natural atmospheric variance / noise
    noise = np.random.normal(0, 3.5, n_samples)
    rainfall_mm = np.maximum(0.0, rainfall_mm + noise)
    
    df = pd.DataFrame({
        'pressure': pressure,
        'humidity': humidity,
        'temp': temperature,
        'rainfall': np.round(rainfall_mm, 1)
    })
    
    return df

def train_and_save_regressor():
    print("🌧️ Generating Atmospheric Training Telemetry...")
    df = generate_atmospheric_dataset()
    
    X = df[['pressure', 'humidity', 'temp']]
    y = df['rainfall']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("⚡ Training XGBoost Rainfall Regressor Model...")
    regressor = XGBRegressor(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        objective='reg:squarederror',
        random_state=42
    )
    
    regressor.fit(X_train, y_train)
    
    # Model evaluation metrics
    predictions = regressor.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    r2 = r2_score(y_test, predictions)
    
    print(f"✅ Model Training Complete!")
    print(f"📊 Performance Metrics -> RMSE: {rmse:.2f} mm | R² Score: {r2:.4f}")
    
    # Ensure models directory exists
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    save_path = os.path.join(models_dir, 'rainfall_regressor.pkl')
    joblib.dump(regressor, save_path)
    print(f"💾 Trained weights successfully saved to: {os.path.abspath(save_path)}")

if __name__ == "__main__":
    train_and_save_regressor()