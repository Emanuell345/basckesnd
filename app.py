# app.py - Backend + Bot Instagram + API (TUDO EM 1 ARQUIVO)
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import threading
import time
import json
import os
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError, PleaseWaitFewMinutes

app = Flask(__name__)
CORS(app)

# =============================================
# ARQUIVOS
# =============================================
DATA = {
    "respondidas": set(),
    "pendentes": set(),
    "vendas": [],
    "session": "session.json"
}

def load_json(key, default):
    file = f"{key}.json"
    if os.path.exists(file):
        try: return json.load(open(file))
        except: return default
    return default

def save_json(key, data):
    with open(f"{key}.json", 'w') as f:
        json.dump(data, f, indent=2)

# Carregar dados
DATA["respondidas"] = set(load_json("respondidas", []))
DATA["pendentes"] = set(load_json("pendentes", []))
DATA["vendas"] = load_json("vendas", [])

# =============================================
# INSTAGRAM BOT
# =============================================
cl = None
bot_running = True

def login_instagram():
    global cl
    cl = Client()
    if os.path.exists(DATA["session"]):
        try:
            cl.load_settings(DATA["session"])
            cl.get_timeline_feed()
            print("Sessão carregada")
            return True
        except: pass

    # LOGIN MANUAL (1ª VEZ)
    USER = os.environ.get("IG_USER", "ladelicato_")
    PASS = os.environ.get("IG_PASS", "jesusteama")
    if USER == "SEU_USUARIO_AQUI": 
        print("Configure IG_USER e IG_PASS no Render")
        return False
    try:
        cl.login(USER, PASS)
        cl.dump_settings(DATA["session"])
        print("Login feito")
        return True
    except Exception as e:
        print("Erro login:", e)
        return False

def bot_loop():
    global cl
    while bot_running:
        if not cl: 
            time.sleep(10)
            continue
        try:
            threads = cl.direct_threads(amount=20)
            for thread in threads:
                if not bot_running: break
                tid = str(thread.id)
                msgs = thread.messages
                if not msgs: continue
                msg = msgs[0]
                if msg.user_id == cl.user_id: continue
                if tid in DATA["respondidas"]: continue

                user = cl.user_info(msg.user_id)
                nome = user.full_name or user.username

                # Salvar pendente
                DATA["pendentes"].add(tid)
                save_json("pendentes", list(DATA["pendentes"]))

                # Responder
                cl.direct_send("Olá! Já avisei o vendedor. Ele te responde em breve!", [thread.id])
                print(f"Respondido: {nome}")

                # Salvar resposta
                DATA["respondidas"].add(tid)
                save_json("respondidas", list(DATA["respondidas"]))

                # Salvar venda
                venda = {
                    "thread_id": tid,
                    "cliente": nome,
                    "valor": 89.90,
                    "data_hora": datetime.now().isoformat()
                }
                DATA["vendas"].append(venda)
                save_json("vendas", DATA["vendas"])

                time.sleep(15)
            time.sleep(30)
        except PleaseWaitFewMinutes:
            print("Pausa do Instagram...")
            time.sleep(300)
        except Exception as e:
            print("Erro bot:", e)
            time.sleep(60)

# Iniciar bot em thread
def start_bot():
    if login_instagram():
        threading.Thread(target=bot_loop, daemon=True).start()

# =============================================
# API ENDPOINTS
# =============================================
@app.route('/api/dashboard/metrics')
def metrics():
    hoje = datetime.now().strftime("%Y-%m-%d")
    vendas_hoje = [v for v in DATA["vendas"] if v["data_hora"][:10] == hoje]
    vendas_mes = [v for v in DATA["vendas"] if v["data_hora"][:7] == hoje[:7]]

    pendentes = len(DATA["pendentes"] - DATA["respondidas"])

    chart = {}
    for v in DATA["vendas"][-7:]:
        dia = v["data_hora"][:10]
        chart[dia] = chart.get(dia, 0) + v["valor"]

    return jsonify({
        "today_sales": sum(v["valor"] for v in vendas_hoje),
        "month_sales": sum(v["valor"] for v in vendas_mes),
        "active_sellers": len(vendas_hoje),
        "pending_clients": pendentes,
        "chart_data": [{"dia": d, "valor": v} for d, v in sorted(chart.items())],
        "recent_sales": sorted(vendas_hoje, key=lambda x: x["data_hora"], reverse=True)[:5],
        "last_update": datetime.now().strftime("%H:%M:%S")
    })

@app.route('/api/health')
def health():
    return jsonify({"status": "online", "bot": "running" if cl else "offline"})

@app.route('/')
def index():
    return "<h1>Ladelicato SaaS Rodando!</h1>"

# =============================================
# INICIAR
# =============================================
if __name__ == '__main__':
    start_bot()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
