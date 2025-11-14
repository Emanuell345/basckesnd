# app.py - Backend com Gráfico e Lista de Clientes
from flask import Flask, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime, date
from collections import defaultdict

app = Flask(__name__)
CORS(app, origins=["*"])

DATA_DIR = '.'

def get_vendas():
    if not os.path.exists('vendas.json'): return []
    try:
        with open('vendas.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return []

def get_chart_data():
    vendas = get_vendas()
    por_dia = defaultdict(float)
    for v in vendas:
        dia = v['data_hora'][:10]
        por_dia[dia] += v['valor']
    return [{"dia": d, "valor": v} for d, v in sorted(por_dia.items())[-7:]]

@app.route('/api/dashboard/metrics')
def metrics():
    vendas = get_vendas()
    hoje = date.today().isoformat()
    vendas_hoje = [v for v in vendas if v['data_hora'][:10] == hoje]
    vendas_mes = [v for v in vendas if v['data_hora'][:7] == hoje[:7]]

    pendentes = 0
    if os.path.exists('pendentes.json') and os.path.exists('respondidas.json'):
        p = set(json.load(open('pendentes.json')))
        r = set(json.load(open('respondidas.json')))
        pendentes = len(p - r)

    return jsonify({
        "today_sales": sum(v['valor'] for v in vendas_hoje),
        "month_sales": sum(v['valor'] for v in vendas_mes),
        "active_sellers": len(vendas_hoje),
        "pending_clients": pendentes,
        "chart_data": get_chart_data(),
        "recent_sales": sorted(vendas_hoje, key=lambda x: x['data_hora'], reverse=True)[:5],
        "last_update": datetime.now().strftime("%H:%M:%S")
    })

@app.route('/api/health')
def health():
    return jsonify({"status": "online", "files": os.listdir(DATA_DIR)})

@app.route('/')
def home():
    return "Ladelicato SaaS - Online"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
