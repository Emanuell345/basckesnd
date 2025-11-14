# app.py - BOT + API + LOGS VISÍVEIS
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import time
import json
import os
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError, PleaseWaitFewMinutes, TwoFactorRequired

app = Flask(__name__)
CORS(app, origins=["https://ladelicato.netlify.app"])

# =============================================
# CONFIGURAÇÃO
# =============================================
SESSION_FILE = "session.json"
RESPONDIDAS_FILE = "respondidas.json"
PENDENTES_FILE = "pendentes.json"
VENDAS_FILE = "vendas.json"

# Variáveis de ambiente (OBRIGATÓRIO)
IG_USER = os.environ.get("IG_USER")
IG_PASS = os.environ.get("IG_PASS")
MENSAGEM = "Olá! Já avisei o vendedor. Ele te responde em breve. Aguarde um momento!"

# Dados em memória
DATA = {
    "respondidas": set(),
    "pendentes": set(),
    "vendas": []
}

# Cliente Instagram
cl = None
bot_running = True

# =============================================
# LOGS COLORIDOS
# =============================================
def log(msg, tipo="INFO"):
    cores = {"INFO": "\033[92m", "ERROR": "\033[91m", "WARNING": "\033[93m"}
    print(f"{cores.get(tipo, '')}[{datetime.now().strftime('%H:%M:%S')}] {tipo}: {msg}\033[0m")

# =============================================
# ARQUIVOS
# =============================================
def load_set(file, default=set()):
    if os.path.exists(file):
        try: return set(json.load(open(file)))
        except: return default
    return default

def save_set(file, s):
    with open(file, 'w') as f:
        json.dump(list(s), f, indent=2)

def load_list(file, default=[]):
    if os.path.exists(file):
        try: return json.load(open(file))
        except: return default
    return default

# Carregar dados
DATA["respondidas"] = load_set(RESPONDIDAS_FILE)
DATA["pendentes"] = load_set(PENDENTES_FILE)
DATA["vendas"] = load_list(VENDAS_FILE)

# =============================================
# LOGIN COM 2FA + SESSÃO
# =============================================
def login():
    global cl
    cl = Client()
    
    # Tentar carregar sessão
    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.get_timeline_feed()
            log("Sessão carregada com sucesso!", "INFO")
            return True
        except Exception as e:
            log(f"Sessão inválida: {e}", "WARNING")
            os.remove(SESSION_FILE)

    # Login novo
    if not IG_USER or not IG_PASS:
        log("IG_USER ou IG_PASS não configurados!", "ERROR")
        return False

    try:
        log(f"Fazendo login como {IG_USER}...")
        cl.login(IG_USER, IG_PASS)
        cl.dump_settings(SESSION_FILE)
        log("Login realizado com sucesso!", "INFO")
        return True
    except TwoFactorRequired:
        code = input("Código 2FA: ").strip()
        try:
            cl.login(IG_USER, IG_PASS, verification_code=code)
            cl.dump_settings(SESSION_FILE)
            log("Login com 2FA OK!", "INFO")
            return True
        except: 
            log("2FA falhou", "ERROR")
            return False
    except Exception as e:
        log(f"Erro no login: {e}", "ERROR")
        return False

# =============================================
# BOT PRINCIPAL
# =============================================
def bot_loop():
    global cl
    while bot_running:
        if not cl:
            time.sleep(10)
            continue

        try:
            threads = cl.direct_threads(amount=15)
            for thread in threads:
                if not bot_running: break
                tid = str(thread.id)
                msgs = thread.messages
                if not msgs: continue
                ultima = msgs[0]
                if ultima.user_id == cl.user_id: continue
                if tid in DATA["respondidas"]: continue

                user = cl.user_info(ultima.user_id)
                nome = user.full_name or user.username

                log(f"Nova DM de {nome}: {ultima.text[:30]}...")

                # Salvar pendente
                DATA["pendentes"].add(tid)
                save_set(PENDENTES_FILE, DATA["pendentes"])

                # Enviar mensagem
                try:
                    cl.direct_send(MENSAGEM, [thread.id])
                    log(f"Mensagem enviada para {nome}!", "INFO")

                    # Salvar resposta
                    DATA["respondidas"].add(tid)
                    save_set(RESPONDIDAS_FILE, DATA["respondidas"])

                    # Salvar venda
                    venda = {
                        "thread_id": tid,
                        "cliente": nome,
                        "valor": 89.90,
                        "data_hora": datetime.now().isoformat()
                    }
                    DATA["vendas"].append(venda)
                    save_set(VENDAS_FILE, DATA["vendas"])

                    time.sleep(20)
                except Exception as e:
                    log(f"Erro ao enviar: {e}", "ERROR")
                    time.sleep(60)

            time.sleep(35)
        except PleaseWaitFewMinutes:
            log("Instagram pediu pausa... esperando 5min", "WARNING")
            time.sleep(300)
        except Exception as e:
            log(f"Erro no bot: {e}", "ERROR")
            time.sleep(60)

# =============================================
# API
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
        "last_update": datetime.now().strftime("%H:%M:%S"),
        "bot_status": "online" if cl else "offline"
    })

@app.route('/api/health')
def health():
    return jsonify({
        "status": "online",
        "bot": "running" if cl else "not started",
        "login": IG_USER is not None
    })

@app.route('/')
def home():
    return "<pre>Ladelicato SaaS Rodando!\nVerifique os logs no Render.</pre>"

# =============================================
# INICIAR
# =============================================
def start_bot():
    if login():
        threading.Thread(target=bot_loop, daemon=True).start()
    else:
        log("Bot não iniciado: falha no login", "ERROR")

if __name__ == '__main__':
    start_bot()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
