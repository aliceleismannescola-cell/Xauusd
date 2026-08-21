import os
import time
import threading
import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf
from flask import Flask

app = Flask(__name__)

TELEGRAM_TOKEN = "8632537313:AAFjidCR7O7t0ofdoCjvpMJi017gQmTN_8U"
CHAT_ID = "1276043677"

@app.route('/')
def home():
    return "Robô Didático XAU/USD Spot rodando! Acesse /enviar para testar e ver o resultado na tela."

def executar_analise_e_envio():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=15m&range=2d"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    res = requests.get(url, headers=headers, timeout=15)
    json_data = res.json()
    
    timestamps = json_data['chart']['result'][0]['timestamp']
    quote = json_data['chart']['result'][0]['indicators']['quote'][0]
    
    df = pd.DataFrame({
        'Open': quote['open'],
        'High': quote['high'],
        'Low': quote['low'],
        'Close': quote['close'],
        'Volume': quote['volume']
    }, index=pd.to_datetime(timestamps, unit='s')).dropna()
    
    offset_spot = 57.0 
    df['Open'] -= offset_spot
    df['High'] -= offset_spot
    df['Low'] -= offset_spot
    df['Close'] -= offset_spot

    df_recorte = df.tail(35).copy()
    df_recorte['EMA9'] = df_recorte['Close'].ewm(span=9, adjust=False).mean()
    df_recorte['EMA21'] = df_recorte['Close'].ewm(span=21, adjust=False).mean()

    preco_atual = float(df_recorte['Close'].iloc[-1])
    ema9_atual = float(df_recorte['EMA9'].iloc[-1])
    ema21_atual = float(df_recorte['EMA21'].iloc[-1])
    resistencia = float(df_recorte['High'].tail(20).max())
    suporte = float(df_recorte['Low'].tail(20).min())

    if preco_atual > ema9_atual and ema9_atual > ema21_atual:
        sinal = "🟢 COMPRA (ALTA)"
        sl, tp = preco_atual - 3.50, preco_atual + 7.00
        explicacao = f"🎓 *AULA COMPLETA: TENDÊNCIA DE ALTA*\n\n📌 *1. Entrada:* ${preco_atual:.2f}\n📌 *2. Take Profit:* ${tp:.2f}\n📌 *3. Stop Loss:* ${sl:.2f}"
    elif preco_atual < ema9_atual and ema9_atual < ema21_atual:
        sinal = "🔴 VENDA (BAIXA)"
        sl, tp = preco_atual + 3.50, preco_atual - 7.00
        explicacao = f"🎓 *AULA COMPLETA: TENDÊNCIA DE BAIXA*\n\n📌 *1. Entrada:* ${preco_atual:.2f}\n📌 *2. Take Profit:* ${tp:.2f}\n📌 *3. Stop Loss:* ${sl:.2f}"
    else:
        sinal = "⚪ NEUTRO (CONSOLIDAÇÃO)"
        explicacao = f"🎓 *AULA COMPLETA: LATERALIZAÇÃO*\n\n📌 *Resistência:* ${resistencia:.2f}\n📌 *Suporte:* ${suporte:.2f}"

    mc = mpf.make_marketcolors(up='#00e676', down='#ff5252', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, gridstyle=':', gridcolor='#333333')
    add_plots = [
        mpf.makeaddplot(df_recorte['EMA9'], color='#00b0ff', width=1.5),
        mpf.makeaddplot(df_recorte['EMA21'], color='#ffd600', width=1.5)
    ]

    linhas_h = [preco_atual, preco_atual+7, preco_atual-3.5] if "COMPRA" in sinal or "VENDA" in sinal else [resistencia, suporte]
    cores_linhas = ['#ffea00', '#00e676', '#ff1744'] if "COMPRA" in sinal or "VENDA" in sinal else ['#ff9100', '#e040fb']

    caminho_imagem = "grafico_aula.png"
    fig, _ = mpf.plot(
        df_recorte, type='candle', style=s, addplot=add_plots,
        title=f"\n XAU/USD SPOT (M15) [{sinal}]",
        hlines=dict(hlines=linhas_h, colors=cores_linhas, linestyle='-.', linewidths=1.2),
        figsize=(11, 6.5), returnfig=True
    )
    fig.savefig(caminho_imagem, bbox_inches='tight', dpi=180)
    plt.close(fig)

    legenda = f"📊 *ESTUDO TÉCNICO - XAU/USD (M15)*\n\n💵 *Preço Spot:* ${preco_atual:.2f}\n🎯 *Sinal:* {sinal}\n\n{explicacao}"
    
    url_tg = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(caminho_imagem, 'rb') as foto:
        res_tg = requests.post(url_tg, data={'chat_id': CHAT_ID, 'caption': legenda, 'parse_mode': 'Markdown'}, files={'photo': foto}, timeout=30)
    
    if os.path.exists(caminho_imagem):
        os.remove(caminho_imagem)
        
    return res_tg.text

@app.route('/enviar')
def enviar_manual():
    try:
        resposta = executar_analise_e_envio()
        return f"<h1>Resultado do Envio:</h1><pre>{resposta}</pre>"
    except Exception as e:
        return f"<h1>Erro ao Executar:</h1><pre>{str(e)}</pre>"

def loop_monitoramento():
    time.sleep(10)
    while True:
        try:
            executar_analise_e_envio()
        except Exception as e:
            print(f"Erro no loop automático: {e}")
        time.sleep(900)

if __name__ == "__main__":
    t = threading.Thread(target=loop_monitoramento)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
