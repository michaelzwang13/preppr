# src/health.py
from flask import Blueprint, jsonify
from src.database import get_db
import os, logging
import requests
import google.generativeai as genai
health_bp = Blueprint("health", __name__)

@health_bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200
  
  
@health_bp.get("/dbping")
def dbping():
    try:
        db = get_db(); 
        with db.cursor() as c: c.execute("SELECT 1")
        return {"db":"ok"}, 200
    except Exception as e:
        return {"db":"error","detail":str(e)}, 500
      
         
log = logging.getLogger("env"); log.setLevel(logging.INFO)

@health_bp.get("/health/env")
def health_env():
    info = {
      "DB_PORT": os.getenv("DB_PORT"),
      "HAS_DB_HOST": bool(os.getenv("DB_HOST")),
      "HAS_LLM_KEY": bool(os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")),
      "HAS_NUTRITIONIX": bool(os.getenv("NUTRITIONIX_API_KEY")),
    }
    log.info(f"ENV CHECK: {info}")
    return info, 200
  

@health_bp.get("/health/nutritionix")
def health_nx():
    url = "https://trackapi.nutritionix.com/v2/search/item"
    headers = {
        "x-app-id": os.getenv("NUTRITIONIX_API_ID", "").strip(),
        "x-app-key": os.getenv("NUTRITIONIX_API_KEY", "").strip(),
        "Accept": "application/json",
    }
    try:
        r = requests.get(url, headers=headers, params={"upc": "077567603005"}, timeout=8)
        # 200 or 404 = network + auth headers OK (UPC not found is fine)
        if r.status_code in (200, 404):
            return {"status":"ok","code":r.status_code}, 200
        # 401 = creds not present or wrong
        if r.status_code == 401:
            return {"status":"auth_fail","code":401}, 500
        return {"status":"nx_error","code":r.status_code,"body":r.text[:200]}, 500
    except Exception as e:
        return {"status":"nx_fail","err":str(e)}, 500
      
      
@health_bp.get("/health/gemini")
def health_gemini():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    try:
        if not api_key:
            return jsonify({"status": "no_api_key"}), 500

        # Configure the SDK
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash-latest")

        # Send a minimal request (super short prompt to minimize cost)
        response = model.generate_content("ping")

        if response and hasattr(response, "text"):
            return jsonify({"status": "ok", "preview": response.text[:50]}), 200
        else:
            return jsonify({"status": "unexpected_response"}), 500

    except Exception as e:
        # This will catch bad key, no egress, SDK import issues, etc.
        return jsonify({"status": "gemini_fail", "err": str(e)}), 500