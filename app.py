# app.py - BACKEND COM EDIÇÃO DE VENDAS + API
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, origins=["https://ladelicato.netlify.app"])

# =============================================
# ARQUIVOS
# =============================================
VENDAS_FILE = "vendas.json"

def load_vendas():
    if os.path.exists(VENDAS_FILE):
        try: return json.load(open(VENDAS_FILE))
        except: return []
    return []

def save_vendas(vendas):
    with open(VENDAS_FILE, 'w') as f:
        json.dump(vendas, f, indent=2)

# =============================================
# API: MÉTRICAS
# =============================================
@app.route('/api/dashboard/metrics')
def metrics():
    vendas = load_vendas()
    hoje = datetime.now().strftime("%Y-%m-%d")
    mes = hoje[:7]

    vendas_hoje = [v for v in vendas if v["data_hora"][:10] == hoje]
    vendas_mes = [v for v in vendas if v["data_hora"][:7] == mes]

    chart = {}
    for v in vendas[-7:]:
        dia = v["data_hora"][:10]
        chart[dia] = chart.get(dia, 0) + v["valor"]

    return jsonify({
        "today_sales": sum(v["valor"] for v in vendas_hoje),
        "month_sales": sum(v["valor"] for v in vendas_mes),
        "active_sellers": len(vendas_hoje),
        "pending_clients": 0,
        "chart_data": [{"dia": d, "valor": v} for d, v in sorted(chart.items())],
        "recent_sales": sorted(vendas_hoje, key=lambda x: x["data_hora"], reverse=True)[:5],
        "last_update": datetime.now().strftime("%H:%M:%S")
    })

# =============================================
# API: ADICIONAR VENDA
# =============================================
@app.route('/api/vendas', methods=['POST'])
def add_venda():
    data = request.json
    vendas = load_vendas()

    nova_venda = {
        "thread_id": f"manual_{len(vendas)}",
        "cliente": data.get("cliente", "Cliente Manual"),
        "valor": float(data.get("valor", 89.90)),
        "data_hora": datetime.now().isoformat()
    }
    vendas.append(nova_venda)
    save_vendas(vendas)
    return jsonify({"status": "ok", "venda": nova_venda})

# =============================================
# API: EDITAR VENDA
# =============================================
@app.route('/api/vendas/<int:index>', methods=['PUT'])
def edit_venda(index):
    data = request.json
    vendas = load_vendas()
    if 0 <= index < len(vendas):
        vendas[index]["valor"] = float(data.get("valor", vendas[index]["valor"]))
        vendas[index]["cliente"] = data.get("cliente", vendas[index]["cliente"])
        save_vendas(vendas)
        return jsonify({"status": "ok", "venda": vendas[index]})
    return jsonify({"error": "índice inválido"}), 400

# =============================================
# API: LISTAR TODAS
# =============================================
@app.route('/api/vendas')
def list_vendas():
    return jsonify(load_vendas())

@app.route('/')
def home():
    return "Ladelicato SaaS - Backend com Edição"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
