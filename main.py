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

# Variável para armazenar o último sinal enviado e evitar spam
ultimo_sinal_enviado = None

@app.route('/')
def home():
    return "Robô Didático XAU/USD Spot rodando! Monitorando o mercado minuto a minuto."

def executar_analise_e_envio(forcar_envio=False):
    global ultimo_sinal_enviado

    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=15m&range=5d"
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

    df_recorte = df.tail(45).copy()
    df_recorte['EMA9'] = df_recorte['Close'].ewm(span=9, adjust=False).mean()
    df_recorte['EMA21'] = df_recorte['Close'].ewm(span=21, adjust=False).mean()

    preco_atual = float(df_recorte['Close'].iloc[-1])
    ema9_atual = float(df_recorte['EMA9'].iloc[-1])
    ema21_atual = float(df_recorte['EMA21'].iloc[-1])
    resistencia = float(df_recorte['High'].tail(25).max())
    suporte = float(df_recorte['Low'].tail(25).min())

    # Determinar sinal
    if preco_atual > ema9_atual and ema9_atual > ema21_atual:
        sinal = "🟢 COMPRA (ALTA)"
        sl, tp = preco_atual - 3.50, preco_atual + 7.00
        explicacao = (
            f"🎓 *OPORTUNIDADE DE COMPRA DECTETADA*\n\n"
            f"📌 *Preço Atual:* ${preco_atual:.2f}\n"
            f"🎯 *Take Profit (TP):* ${tp:.2f} (+7.00)\n"
            f"🛡️ *Stop Loss (SL):* ${sl:.2f} (-3.50)\n\n"
            f"💡 *Análise:* Estrutura de alta confirmada (EMA9 > EMA21)."
        )
    elif preco_atual < ema9_atual and ema9_atual < ema21_atual:
        sinal = "🔴 VENDA (BAIXA)"
        sl, tp = preco_atual + 3.50, preco_atual - 7.00
        explicacao = (
            f"🎓 *OPORTUNIDADE DE VENDA DETECTADA*\n\n"
            f"📌 *Preço Atual:* ${preco_atual:.2f}\n"
            f"🎯 *Take Profit (TP):* ${tp:.2f} (-7.00)\n"
            f"🛡️ *Stop Loss (SL):* ${sl:.2f} (+3.50)\n\n"
            f"💡 *Análise:* Estrutura de baixa confirmada (EMA9 < EMA21)."
        )
    else:
        sinal = "⚪ NEUTRO (CONSOLIDAÇÃO)"
        explicacao = (
            f"🎓 *MERCADO EM CONSOLIDAÇÃO*\n\n"
            f"📌 *Preço Atual:* ${preco_atual:.2f}\n"
            f"🔴 *Resistência:* ${resistencia:.2f}\n"
            f"🟢 *Suporte:* ${suporte:.2f}\n\n"
            f"💡 *Análise:* O preço está lateralizado. Aguardando definição de tendência."
        )

    # Se não for forçado e o sinal for igual ao último enviado, não reenvia para evitar spam
    if not forcar_envio and sinal == ultimo_sinal_enviado:
        return "Nenhuma mudança de sinal. Aguardando nova oportunidade."

    ultimo_sinal_enviado = sinal

    mc = mpf.make_marketcolors(
        up='#00e676', down='#ff5252',
        edge={'up': '#00e676', 'down': '#ff5252'},
        wick={'up': '#00e676', 'down': '#ff5252'},
        volume='in'
    )
    
    style_custom = mpf.make_mpf_style(
        base_mpf_style='charcoal',
        marketcolors=mc,
        facecolor='#121824',
        edgecolor='#1f293d',
        figcolor='#0d1117',
        gridcolor='#1f293d',
        gridstyle='--',
        rc={'font.family': 'sans-serif', 'font.size': 9}
    )

    add_plots = [
        mpf.make_addplot(df_recorte['EMA9'], color='#00b0ff', width=1.8),
        mpf.make_addplot(df_recorte['EMA21'], color='#ffd600', width=1.8)
    ]

    linhas_h = [preco_atual, preco_atual+7.0, preco_atual-3.5] if "COMPRA" in sinal or "VENDA" in sinal else [resistencia, suporte]
    cores_linhas = ['#ffd600', '#00e676', '#ff5252'] if "COMPRA" in sinal or "VENDA" in sinal else ['#ff9100', '#00e676']

    caminho_imagem = "grafico_aula.png"
    
    fig, axes = mpf.plot(
        df_recorte,
        type='candle',
        style=style_custom,
        addplot=add_plots,
        title=dict(title=f"  XAU/USD SPOT (M15)  |  {sinal}", color='#ffffff', fontsize=12, weight='bold'),
        hlines=dict(hlines=linhas_h, colors=cores_linhas, linestyle='--', linewidths=1.2),
        figsize=(10, 5.5),
        datetime_format='%H:%M',
        xrotation=0,
        returnfig=True
    )

    axes[0].set_ylabel('Preço (USD)', color='#8b949e', fontsize=9)
    axes[0].tick_params(colors='#8b949e')
    
    fig.savefig(caminho_imagem, bbox_inches='tight', dpi=200, facecolor='#0d1117')
    plt.close(fig)

    legenda = (
        f"📊 *ESTUDO TÉCNICO - XAU/USD (M15)*\n\n"
        f"💵 *Preço Spot:* ${preco_atual:.2f}\n"
        f"🎯 *Sinal:* {sinal}\n\n"
        f"{explicacao}"
    )
    
    url_tg = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(caminho_imagem, 'rb') as foto:
        res_tg = requests.post(url_tg, data={'chat_id': CHAT_ID, 'caption': legenda, 'parse_mode': 'Markdown'}, files={'photo': foto}, timeout=30)
    
    if os.path.exists(caminho_imagem):
        os.remove(caminho_imagem)
        
    return res_tg.text

@app.route('/enviar')
def enviar_manual():
    try:
        resposta = executar_analise_e_envio(forcar_envio=True)
        return f"<h1>Resultado do Envio:</h1><pre>{resposta}</pre>"
    except Exception as e:
        return f"<h1>Erro ao Executar:</h1><pre>{str(e)}</pre>"

def loop_monitoramento():
    time.sleep(5)
    while True:
        try:
            executar_analise_e_envio(forcar_envio=False)
        except Exception as e:
            print(f"Erro no loop automático: {e}")
        # Checa a cada 60 segundos (1 minuto)
        time.sleep(60)

if __name__ == "__main__":
    t = threading.Thread(target=loop_monitoramento)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
