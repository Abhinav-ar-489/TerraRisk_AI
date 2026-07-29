import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier

print("Re-generating Geological Training Datasets with Smooth Probability Gradients...")
np.random.seed(42)
num_samples = 3000

# Features: Slope, Elevation, Soil_Type, Rainfall_72h, Soil_Saturation
slope = np.random.uniform(5, 45, num_samples)
elevation = np.random.uniform(10, 1500, num_samples)
soil_type = np.random.choice([1, 2, 3], size=num_samples, p=[0.4, 0.4, 0.2])
rainfall = np.random.uniform(0, 500, num_samples)
saturation = np.random.uniform(0.1, 1.0, num_samples)

# Calculate a continuous landscape hazard score
base_score = (slope * 1.5) + (rainfall * 0.4) + (saturation * 45) - (elevation * 0.01)
soil_modifiers = np.where(soil_type == 1, 20, np.where(soil_type == 2, 5, -20))
total_hazard_score = base_score + soil_modifiers

# 🎯 THE TRICK: Introduce a sigmoid-like probability curve with fuzzy noise
# This stops the model from seeing strict cuts and forces it to learn gradients (in-between values)
noise = np.random.normal(0, 15, num_samples)
probability_curve = 1 / (1 + np.exp(-(total_hazard_score - 110) / 15))
y = np.where(np.random.uniform(0, 1, num_samples) < probability_curve, 1, 0)

df = pd.DataFrame({
    'Slope_Angle': slope, 'Elevation': elevation, 'Soil_Type': soil_type,
    'Rainfall_72h': rainfall, 'Soil_Saturation': saturation, 'Landslide_Risk': y
})

os.makedirs("models", exist_ok=True)

print("Training Smooth Inference Core (Soften tree parameters)...")
X = df[['Slope_Angle', 'Elevation', 'Soil_Type', 'Rainfall_72h', 'Soil_Saturation']]
y_target = df['Landslide_Risk']

X_train, X_test, y_train, y_test = train_test_split(X, y_target, test_size=0.2, random_state=42)

# By lowering max_depth to 3 and min_samples_leaf, the trees don't overfit to 0/100.
# They output smooth, continuous probability estimates!
model = GradientBoostingClassifier(
    n_estimators=80, 
    learning_rate=0.08, 
    max_depth=3, 
    min_samples_leaf=5,
    random_state=42
)
model.fit(X_train, y_train)

joblib.dump(model, "models/landslide_model.pkl")
print("SUCCESS! Smooth Probability ML Brain saved to 'models/landslide_model.pkl'")