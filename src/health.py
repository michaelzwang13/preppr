# src/health.py
from flask import Blueprint, jsonify
from src.database import get_db
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