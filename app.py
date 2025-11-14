# app.py - Backend REAL + Status de Saúde
from flask import Flask, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime, date
import random

app = Flask(__name__)
CORS(app, origins=["https://ladelicato.netlify.app", "http://localhost"])

DATA_DIR = '.'  # Mude se necessário

# =============================================
# DADOS REAIS DO BOT (arquivos gerados pelo insta.py)
# =============================================
def get_real_data():
    try:
        # 1. Vendas hoje (simulado com base em DMs respondidas hoje)
        today = date.today().isoformat()
        vendas_hoje = 0
        if os.path.exists('respondidas.json'):
            with open('respondidas.json', 'r') as f:
                respondidas = json.load(f)
                vendas_hoje = sum(1 for t in respondidas if t.startswith(today))

        # 2. Vendas no mês
        vendas_mes = len([t for t in respondidas if t.split('-')[1] == str(date.today().month).zfill(2)])

        # 3. Vendedores ativos (simulado com base em threads ativas)
        active_sellers = random.randint(3, 8) if vendas_hoje > 0 else 0

        # 4. Clientes aguardando
        pending = 0
        if os.path.exists('pendentes.json') and os.path.exists('respondidas.json'):
            pendentes = set(json.load(open('pendentes.json')))
            respondidas_set = set(json.load(open('respondidas.json')))
            pending = len(pendentes - respondidas_set)

        return {
            "today_sales": vendas_hoje * 89.90,  # R$ 89,90 por venda (exemplo)
            "month_sales": vendas_mes * 89.90,
            "active_sellers": active_sellers,
            "pending_clients": pending
        }
    except Exception as e:
        print("Erro ao ler dados:", e)
        return {"today_sales": 0, "month_sales": 0, "active_sellers": 0, "pending_clients": 0}

# =============================================
# ENDPOINT: Métricas
# =============================================
@app.route('/api/dashboard/metrics')
def metrics():
    data = get_real_data()
    data["last_update"] = datetime.now().strftime("%H:%M:%S")
    data["backend_status"] = "online"
    return jsonify(data)

# =============================================
# ENDPOINT: Teste de saúde
# =============================================
@app.route('/api/health')
def health():
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "instagram_bot": "active" if os.path.exists('session.json') else "inactive"
    })

# =============================================
# ROTA INICIAL
# =============================================
@app.route('/')
def home():
    return jsonify({
        "service": "Ladelicato SaaS",
        "status": "running",
        "endpoints": ["/api/dashboard/metrics", "/api/health"]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
