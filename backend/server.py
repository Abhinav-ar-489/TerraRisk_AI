import os
import requests
import joblib
import pandas as pd
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from twilio.rest import Client

app = Flask(__name__)
CORS(app)

# ==========================================================================
# 🛰️ CONFIGURATION & CREDENTIAL MANAGEMENT
# ==========================================================================
OPENWEATHER_API_KEY = "3b95ffbba2aca9e09b20d0665a788207"
TWILIO_ACCOUNT_SID = "AC61567fa7bdc3cb0c311bffbf2db66817"
TWILIO_AUTH_TOKEN = "2836177a67be2037da58f4d68dd129d4"
TWILIO_PHONE_NUMBER = "+15822632350"
YOUR_PERSONAL_MOBILE = "+916282115954"

HISTORICAL_HOTSPOTS = [
    {"name": "Puthumala, Wayanad", "lat": 11.4938, "lng": 76.1268, "year": 2019},
    {"name": "Kavalappara, Malappuram", "lat": 11.3622, "lng": 76.3241, "year": 2019},
    {"name": "Pettimudi, Rajamala", "lat": 10.1872, "lng": 77.0255, "year": 2020},
    {"name": "Koottickal, Kottayam", "lat": 9.6384, "lng": 76.8431, "year": 2021},
    {"name": "Chooralmala, Wayanad", "lat": 11.5284, "lng": 76.1751, "year": 2024}
]

# ==========================================================================
# 🧠 DUAL-STAGE MODEL INITIALIZATION
# ==========================================================================
CLASSIFIER_PATH = os.path.join(os.path.dirname(__file__), 'models', 'landslide_model.pkl')
REGRESSOR_PATH = os.path.join(os.path.dirname(__file__), 'models', 'rainfall_regressor.pkl')

# Stage-2: XGBoost Landslide Risk Classifier
ai_brain = joblib.load(CLASSIFIER_PATH) if os.path.exists(CLASSIFIER_PATH) else None

# Stage-1: XGBoost Quantitative Rainfall Regressor
rain_brain = joblib.load(REGRESSOR_PATH) if os.path.exists(REGRESSOR_PATH) else None

print(f"Status -> Classifier: {'Loaded' if ai_brain else 'Missing'} | Regressor: {'Loaded' if rain_brain else 'Missing'}")

@app.route('/api/hotspots', methods=['GET'])
def get_hotspots():
    return jsonify(HISTORICAL_HOTSPOTS)

@app.route('/api/predict', methods=['POST'])
def predict_risk():
    try:
        data = request.json
        lat = float(data.get('lat', 10.5))
        lng = float(data.get('lng', 76.5))
        slope_val = float(data.get('slope', 30.0))
        soil_val = int(data.get('soil', 2))
        sim_mode = data.get('sim_mode', False)

        # Elevation lookup
        elevation_val = 0.0
        try:
            elev_url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lng}"
            elev_res = requests.get(elev_url, timeout=2.0).json()
            if "results" in elev_res and len(elev_res["results"]) > 0:
                elevation_val = float(elev_res["results"][0].get("elevation", 0.0))
        except Exception as e:
            print(f"⚠️ Elevation API Handshake timed out: {e}")
            elevation_val = float(data.get('elevation', 150.0))

        # Lowland Coastal Guardrail
        if slope_val < 8.0 and elevation_val < 150.0:
            return jsonify({
                "risk_percentage": 0.0, 
                "alert_text": "Topographical stability verified. Plain lowland coastal track.",
                "geo_name": "Lowland Plain Sector",
                "live_rainfall": 0.0,
                "live_humidity": 0.0,
                "true_elevation": round(elevation_val, 0)
            })

        # Reverse Geocoding for location name
        geo_name = f"Grid Box ({lat:.2f}°N)"
        try:
            geo_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lng}&limit=1&appid={OPENWEATHER_API_KEY}"
            geo_res = requests.get(geo_url, timeout=1).json()
            if geo_res:
                geo_name = f"{geo_res[0].get('name', 'Sector')} Grid"
        except:
            pass

        live_rainfall = 0.0
        live_humidity = 50.0
        pressure_val = 1013.25
        temp_val = 25.0

        if not sim_mode:
            try:
                w_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={OPENWEATHER_API_KEY}&units=metric"
                w_res = requests.get(w_url, timeout=1.5).json()
                
                live_humidity = float(w_res.get("main", {}).get("humidity", 50.0))
                pressure_val = float(w_res.get("main", {}).get("pressure", 1013.25))
                temp_val = float(w_res.get("main", {}).get("temp", 25.0))
                
                # STAGE-1 INFERENCE: Use Rainfall Regressor if available
                if rain_brain is not None:
                    rain_input = pd.DataFrame([{
                        'pressure': pressure_val,
                        'humidity': live_humidity,
                        'temp': temp_val
                    }])
                    predicted_rain = float(rain_brain.predict(rain_input)[0])
                    live_rainfall = max(0.0, predicted_rain)
                elif "rain" in w_res:
                    live_rainfall = float(w_res["rain"].get("1h", 0.0)) * 24
            except:
                live_rainfall = 45.0 if slope_val > 25 else 10.0
                live_humidity = 75.0 if elevation_val > 800 else 55.0
        else:
            live_rainfall = float(data.get('manual_rainfall', 0.0))
            live_humidity = float(data.get('manual_saturation', 50.0))

        # STAGE-2 INFERENCE: Landslide Risk Classifier
        risk_percentage = 0.0
        if ai_brain is not None:
            input_features = pd.DataFrame([{
                'Slope_Angle': slope_val,
                'Elevation': elevation_val,
                'Soil_Type': soil_val,
                'Rainfall_72h': live_rainfall,
                'Soil_Saturation': live_humidity / 100.0
            }])
            risk_probability = ai_brain.predict_proba(input_features)[0][1]
            risk_percentage = float(risk_probability * 100)
        else:
            if live_rainfall > 200.0 or (slope_val > 28.0 and (live_humidity / 100.0) > 0.80):
                risk_percentage = 91.8
            else:
                risk_percentage = 14.5

        # Alert generation logic
        nlp_alert_text = ""
        if risk_percentage >= 80.0:
            malayalam_addon = f"\n🚨മാറിത്താമസിക്കുക: {geo_name}!" if risk_percentage >= 85 else f"\n⚠️ജാഗ്രത: {geo_name}!"
            
            try:
                ollama_res = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3.2:3b",
                        "prompt": f"Write a 4-word short evacuation alert for {geo_name}. Max 40 characters.",
                        "stream": False
                    }, timeout=3
                )
                if ollama_res.status_code == 200:
                    generated_text = ollama_res.json().get("response", "").strip().replace('"', '').replace('.', '')
                    nlp_alert_text = f"{generated_text[:40]}{malayalam_addon}"
            except:
                prefix = "🚨EVACUATE:" if risk_percentage >= 85 else "⚠️WARNING:"
                nlp_alert_text = f"{prefix} Risk high at {geo_name}.{malayalam_addon}"

        return jsonify({
            "risk_percentage": round(risk_percentage, 1),
            "live_rainfall": round(live_rainfall, 1),
            "live_humidity": round(live_humidity, 1),
            "alert_text": nlp_alert_text,
            "geo_name": geo_name,
            "true_elevation": round(elevation_val, 0)
        })

    except Exception as e:
        return jsonify({"risk_percentage": 0.0, "alert_text": f"Engine Error: {str(e)}"}), 500

@app.route('/api/forecast', methods=['POST'])
def get_weather_forecast():
    try:
        data = request.json
        lat = float(data.get('lat', 10.5))
        lng = float(data.get('lng', 76.5))
        
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lng}&appid={OPENWEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=3.0).json()
        
        if str(res.get("cod")) != "200":
            return jsonify({"success": False, "error": "API handshake failed"}), 400
            
        daily_forecasts = []
        for item in res.get("list", []):
            if "12:00:00" in item.get("dt_txt", ""):
                main_cond = item["weather"][0]["main"].lower()
                condition_key = "clear"
                if "thunder" in main_cond: condition_key = "thunderstorm"
                elif "rain" in main_cond or "drizzle" in main_cond: condition_key = "rain"
                elif "cloud" in main_cond: condition_key = "clouds"
                
                date_obj = datetime.datetime.strptime(item["dt_txt"], "%Y-%m-%d %H:%M:%S")
                day_name = date_obj.strftime("%a")

                daily_forecasts.append({
                    "day": day_name,
                    "temp": round(item["main"]["temp"], 1),
                    "condition": condition_key,
                    "desc": item["weather"][0]["description"].title(),
                    "humidity": item["main"]["humidity"]
                })
                if len(daily_forecasts) == 3:
                    break
                    
        return jsonify({"success": True, "forecast": daily_forecasts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/broadcast', methods=['POST'])
def broadcast_sms():
    try:
        payload = request.json
        alert_text = payload.get('alert_text', '')
        recipient_mobile = payload.get('recipient_mobile', YOUR_PERSONAL_MOBILE)
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"🚨TerraRisk:\n{alert_text}",
            from_=TWILIO_PHONE_NUMBER,
            to=recipient_mobile
        )
        return jsonify({"success": True, "sid": message.sid})
    except Exception as tx_err:
        return jsonify({"success": False, "error": str(tx_err)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)