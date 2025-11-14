# app.py - Backend Flask para Dashboard SaaS (Instagram DMs)
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import random
import os
from datetime import datetime

app = Flask(__name__, static_folder=None)
CORS(app)  # Permite Netlify acessar

# =============================================
# PASTA DE ARQUIVOS DO BOT (mesmo diretório)
# =============================================
DATA_DIR = '.'  # mesmo local do app.py

# =============================================
# FUNÇÃO: Clientes aguardando atendimento (Instagram DMs)
# =============================================
def get_pending_clients():
    try:
        respondidas_path = os.path.join(DATA_DIR, 'respondidas.json')
        pendentes_path = os.path.join(DATA_DIR, 'pendentes.json')

        # Carrega quem já respondeu
        respondidas = set()
        if os.path.exists(respondidas_path):
            with open(respondidas_path, 'r', encoding='utf-8') as f:
                respondidas = set(json.load(f))

        # Carrega quem mandou mensagem
        pendentes = set()
        if os.path.exists(pendentes_path):
            with open(pendentes_path, 'r', encoding='utf-8') as f:
                pendentes = set(json.load(f))

        # Clientes que mandaram DM mas NÃO foram respondidos
        return len(pendentes - respondidas)
    except Exception as e:
        print(f"Erro ao calcular pendentes: {e}")
        return 0

# =============================================
# ENDPOINT: Métricas do Dashboard
# =============================================
@app.route('/api/dashboard/metrics')
def metrics():
    pending = get_pending_clients()
    return jsonify({
        "today_sales": round(random.uniform(1200, 4800), 2),
        "month_sales": round(random.uniform(28000, 92000), 2),
        "active_sellers": random.randint(7, 16),
        "pending_clients": pending,
        "last_update": datetime.now().strftime("%H:%M:%S")
    })

# =============================================
# ROTA INICIAL (saúde do servidor)
# =============================================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Ladelicato SaaS Backend",
        "instagram_integration": "active",
        "pending_clients": get_pending_clients()
    })

# =============================================
# INICIAR SERVIDOR
# =============================================
if __name__ == '__main__':
    print("Ladelicato SaaS Backend")
    print("Instagram DMs → Dashboard")
    print("Acesse: http://localhost:5000")
    print("API: /api/dashboard/metrics")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=False)
