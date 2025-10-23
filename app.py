import os, json, time
from datetime import datetime
from typing import List, Dict, Any
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://www.findalleasy.com").split(",")
COMMISSION_RATE = float(os.getenv("COMMISSION_RATE", "0.15"))
FX_BASE = os.getenv("FX_BASE", "TRY")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "6"))

VAT = {"TR":0.00,"DE":0.19,"FR":0.20,"ES":0.21,"GB":0.20,"US":0.00,"RU":0.20,"JP":0.10,"AE":0.05,"EU":0.20}

app = Flask(__name__)
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=False)

def now_iso():
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

def fx_rates(base: str = FX_BASE):
    url = f"https://api.exchangerate.host/latest?base={base}"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        rates = data.get("rates", {})
        if base not in rates:
            rates[base] = 1.0
        return rates
    except Exception:
        return {"TRY":1.0,"USD":0.034,"EUR":0.031,"GBP":0.026,"JPY":5.2,"RUB":3.2,"AED":0.125}

def to_try(price: float, currency: str, rates):
    currency = (currency or "TRY").upper()
    if currency == "TRY":
        return price
    if currency not in rates or "TRY" not in rates:
        return price
    return price * (1.0 / (rates.get(currency) or 1.0))

def apply_commission(price: float, rate: float = COMMISSION_RATE) -> float:
    return round(price * (1.0 - rate), 2)

def apply_vat(price_try: float, country_code: str = "TR") -> float:
    vat = VAT.get(country_code.upper(), 0.0)
    return round(price_try * (1.0 + vat), 2)

def provider_amazon(query: str):
    return [{"title": f"{query} (Base)","site":"Amazon","price":1299.0,"currency":"USD","url":"https://www.amazon.com/s?k="+query}]

def provider_trendyol(query: str):
    return [{"title": f"{query} Uyumlu","site":"Trendyol","price":42999.0,"currency":"TRY","url":"https://www.trendyol.com/sr?q="+query}]

def provider_hepsiburada(query: str):
    return [{"title": f"{query} Serisi","site":"Hepsiburada","price":41999.0,"currency":"TRY","url":"https://www.hepsiburada.com/ara?q="+query}]

PROVIDERS = [provider_amazon, provider_trendyol, provider_hepsiburada]

from flask import Response

@app.route("/api/health")
def health():
    return jsonify({"status":"ok","time":now_iso(),"service":"findalleasy-ai-engine-v1"})

@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    region = (request.args.get("region") or "TR").upper()
    lang = (request.args.get("lang") or "tr").lower()
    if not q:
        return jsonify({"error":"missing q"}), 400

    rates = fx_rates(FX_BASE)
    raw = []
    for p in PROVIDERS:
        try:
            raw.extend(p(q))
        except Exception:
            pass

    enriched = []
    for item in raw:
        original_price = float(item.get("price", 0.0))
        currency = item.get("currency", "TRY").upper()
        price_try = to_try(original_price, currency, rates)
        price_try_vat = apply_vat(price_try, region)
        discounted = apply_commission(price_try_vat, COMMISSION_RATE)

        enriched.append({
            "title": item.get("title"),
            "site": item.get("site"),
            "product_url": item.get("url"),
            "original_price": original_price,
            "original_currency": currency,
            "price_try": round(price_try, 2),
            "price_try_with_vat": round(price_try_vat, 2),
            "our_price_try": discounted
        })

    enriched.sort(key=lambda x: x["our_price_try"] or 0)

    return jsonify({
        "query": q,
        "region": region,
        "language": lang,
        "commission_rate": COMMISSION_RATE,
        "fx_base": FX_BASE,
        "count": len(enriched),
        "results": enriched,
        "time": now_iso()
    })

@app.route("/api/trends")
def trends():
    region = (request.args.get("region") or "TR").upper()
    demo = {"TR":["Çiçek Buketi","AirPods Pro","Dyson Süpürge","Otel İstanbul"],
            "DE":["iPhone 15","Dyson V15","Hotel Berlin","Nike Air Max"],
            "US":["MacBook Air","AirPods Pro","Hotel NYC","Nintendo Switch"]}
    items = demo.get(region, demo["TR"])
    return jsonify({"region": region, "trends": items, "time": now_iso()})

@app.route("/api/recommendations")
def recommendations():
    user = request.args.get("user") or "guest"
    last = request.args.get("last") or "iPhone"
    recs = [{"title": f"{last} Case", "site": "Amazon"},
            {"title": f"{last} Charger", "site": "Hepsiburada"},
            {"title": f"{last} Screen Protector", "site": "Trendyol"}]
    return jsonify({"user": user, "items": recs, "time": now_iso()})

@app.route("/ping")
def ping():
    return jsonify({"status": "ok"})
    
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)


