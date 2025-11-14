# app.py - SaaS COMPLETO + ANTI-BLOCK + PROXY OPCIONAL
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import time
import json
import os
import requests
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import *

app = Flask(__name__)
CORS(app, origins=["https://ladelicato.netlify.app"])

# =============================================
# CONFIGURAÇÃO
# =============================================
SESSION_FILE = "session.json"
RESPONDIDAS_FILE = "respondidas.json"
PENDENTES_FILE = "pendentes.json"
VENDAS_FILE = "vendas.json"

IG_USER = os.environ.get("IG_USER")
IG_PASS = os.environ.get("IG_PASS")
USE_PROXY = os.environ.get("USE_PROXY", "False").lower() == "true"
PROXY_URL = os.environ.get("PROXY_URL", "")  # ex: http://user:pass@ip:port

MENSAGEM = "Olá! Já avisei o vendedor. Ele te responde em breve. Aguarde!"

# Dados
DATA = {"respondidas": set(), "pendentes": set(), "vendas": []}
cl = None
bot_running = True

# =============================================
# LOGS
# =============================================
def log(msg, tipo="INFO"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {tipo}: {msg}")

# =============================================
# ARQUIVOS
# =============================================
def load(file, default):
    if os.path.exists(file):
        try: return json.load(open(file))
        except: return default
    return default

def save(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

DATA["respondidas"] = set(load(RESPONDIDAS_FILE, []))
DATA["pendentes"] = set(load(PENDENTES_FILE, []))
DATA["vendas"] = load(VENDAS_FILE, [])

# =============================================
# PROXY (ANTI-BLOCK)
# =============================================
def get_proxy():
    if not USE_PROXY or not PROXY_URL: return None
    return {"http": PROXY_URL, "https": PROXY_URL}

# =============================================
# LOGIN COM PROXY + 2FA
# =============================================
def login():
    global cl
    cl = Client()
    cl.proxy = get_proxy()  # ← ANTI-BLOCK

    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.get_timeline_feed()
            log("Sessão carregada")
            return True
        except: 
            os.remove(SESSION_FILE)

    if not IG_USER or not IG_PASS:
        log("IG_USER/IG_PASS não configurados!", "ERROR")
        return False

    try:
        log(f"Login com {IG_USER}...")
        cl.login(IG_USER, IG_PASS)
        cl.dump_settings(SESSION_FILE)
        log("Login OK")
        return True
    except TwoFactorRequired:
        code = input("Código 2FA: ")
        cl.login(IG_USER, IG_PASS, verification_code=code)
        cl.dump_settings(SESSION_FILE)
        log("2FA OK")
        return True
    except Exception as e:
        log(f"Login falhou: {e}", "ERROR")
        return False

# =============================================
# BOT COM ANTI-BLOCK
# =============================================
def bot_loop():
    global cl
    while bot_running:
        if not cl:
            time.sleep(10)
            continue

        try:
            threads = cl.direct_threads(amount=12)
            for thread in threads:
                tid = str(thread.id)
                if tid in DATA["respondidas"]: continue
                msg = thread.messages[0]
                if msg.user_id == cl.user_id: continue

                user = cl.user_info(msg.user_id)
                nome = user.full_name or user.username
                log(f"DM de {nome}")

                DATA["pendentes"].add(tid)
                save(PENDENTES_FILE, list(DATA["pendentes"]))

                try:
                    cl.direct_send(MENSAGEM, [thread.id])
                    log(f"ENVIADO para {nome}")

                    DATA["respondidas"].add(tid)
                    save(RESPONDIDAS_FILE, list(DATA["respondidas"]))

                    venda = {
                        "thread_id": tid,
                        "cliente": nome,
                        "valor": 89.90,
                        "data_hora": datetime.now().isoformat()
                    }
                    DATA["vendas"].append(venda)
                    save(VENDAS_FILE, DATA["vendas"])

                    time.sleep(25 + int(time.time() % 10))  # ← ANTI-BLOCK
                except:
                    log("Erro ao enviar", "ERROR")
                    time.sleep(60)

            time.sleep(40)
        except PleaseWaitFewMinutes:
            log("Pausa forçada: 5min", "WARNING")
            time.sleep(300)
        except:
            time.sleep(60)

# =============================================
# API
# =============================================
@app.route('/api/dashboard/metrics')
def metrics():
    hoje = datetime.now().strftime("%Y-%m-%d")
    vendas_hoje = [v for v in DATA["vendas"] if v["data_hora"][:10] == hoje]
    pendentes = len(DATA["pendentes"] - DATA["respondidas"])

    chart = {}
    for v in DATA["vendas"][-7:]:
        dia = v["data_hora"][:10]
        chart[dia] = chart.get(dia, 0) + v["valor"]

    return jsonify({
        "today_sales": sum(v["valor"] for v in vendas_hoje),
        "month_sales": sum(v["valor"] for v in [v for v in DATA["vendas"] if v["data_hora"][:7] == hoje[:7]]),
        "active_sellers": len(vendas_hoje),
        "pending_clients": pendentes,
        "chart_data": [{"dia": d, "valor": v} for d, v in sorted(chart.items())],
        "recent_sales": sorted(vendas_hoje, key=lambda x: x["data_hora"], reverse=True)[:5],
        "last_update": datetime.now().strftime("%H:%M:%S")
    })

@app.route('/api/health')
def health():
    return jsonify({"status": "online", "bot": bool(cl)})

# =============================================
# INICIAR
# =============================================
def start_bot():
    if login():
        threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == '__main__':
    start_bot()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
