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
CHAT_ID = "@xaubotMTE"

@app.route('/')
def home():
    return "Robô XAU/USD Spot - Mapeamento Estrito SMC + IFR Rodando!"

def calcular_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def identificar_smc(df):
    """Mapeia Pivôs de Alta e Baixa, BOS e CHoCH"""
    highs = df['High'].values
    lows = df['Low'].values
    closes = df['Close'].values
    
    swing_highs = []
    swing_lows = []
    
    for i in range(2, len(df) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            swing_highs.append((i, highs[i]))
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            swing_lows.append((i, lows[i]))
            
    ultimo_topo = swing_highs[-1][1] if swing_highs else highs.max()
    ultimo_fundo = swing_lows[-1][1] if swing_lows else lows.min()
    
    preco_atual = closes[-1]
    preco_anterior = closes[-2]
    
    evento_smc = "CONSOLIDAÇÃO"
    if preco_anterior <= ultimo_topo and preco_atual > ultimo_topo:
        evento_smc = "BOS ALTA"
    elif preco_anterior >= ultimo_fundo and preco_atual < ultimo_fundo:
        evento_smc = "BOS BAIXA"
        
    return ultimo_topo, ultimo_fundo, evento_smc

def executar_analise_e_envio():
    print("-> Analisando filtros estritos para XAU/USD...")
    
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

    df_recorte = df.tail(60).copy()
    df_recorte['EMA9'] = df_recorte['Close'].ewm(span=9, adjust=False).mean()
    df_recorte['EMA21'] = df_recorte['Close'].ewm(span=21, adjust=False).mean()
    df_recorte['RSI'] = calcular_rsi(df_recorte['Close'], window=14)

    topo_smc, fundo_smc, evento_smc = identificar_smc(df_recorte)

    preco_atual = float(df_recorte['Close'].iloc[-1])
    ema9_atual = float(df_recorte['EMA9'].iloc[-1])
    ema21_atual = float(df_recorte['EMA21'].iloc[-1])
    rsi_atual = float(df_recorte['RSI'].iloc[-1])

    c_open = float(df_recorte['Open'].iloc[-1])
    c_high = float(df_recorte['High'].iloc[-1])
    c_low = float(df_recorte['Low'].iloc[-1])
    c_close = float(df_recorte['Close'].iloc[-1])
    
    corpo = abs(c_close - c_open)
    pavio_superior = c_high - max(c_open, c_close)
    pavio_inferior = min(c_open, c_close) - c_low

    sinal = None
    explicacao = ""

    # CONDICIONAL ESTRITA DE COMPRA:
    # 1. Tendência por Médias Móveis
    # 2. IFR estritamente entre 55 e 65
    # 3. Confirmação de BOS de Alta
    # 4. Sem pavio longo de rejeição no topo
    if preco_atual > ema9_atual and ema9_atual > ema21_atual:
        if 55.0 <= rsi_atual <= 65.0 and evento_smc == "BOS ALTA":
            if not (pavio_superior > (corpo * 1.5) and pavio_superior > 1.2):
                sinal = "🟢 COMPRA CONFIRMADA (SMC + IFR)"
                sl = preco_atual - 3.50
                tp = preco_atual + 7.00
                explicacao = (
                    f"🎯 *SINAL DE ALTA FIDELIDADE (COMPRA)*\n\n"
                    f"📌 *Preço Entrada:* ${preco_atual:.2f}\n"
                    f"🎯 *Take Profit:* ${tp:.2f} (+7.00)\n"
                    f"🛡️ *Stop Loss:* ${sl:.2f} (-3.50)\n"
                    f"📊 *IFR (RSI):* {rsi_atual:.1f} (Ideal: 55-65)\n"
                    f"🏔️ *BOS:* Topo rompido em ${topo_smc:.2f}\n\n"
                    f"💡 *Confluência:* Tendência + Rompimento Estrutural + Impulso IFR."
                )

    # CONDICIONAL ESTRITA DE VENDA:
    # 1. Tendência por Médias Móveis
    # 2. IFR estritamente entre 35 e 45
    # 3. Confirmação de BOS de Baixa
    # 4. Sem pavio longo de absorção no fundo
    elif preco_atual < ema9_atual and ema9_atual < ema21_atual:
        if 35.0 <= rsi_atual <= 45.0 and evento_smc == "BOS BAIXA":
            if not (pavio_inferior > (corpo * 1.5) and pavio_inferior > 1.2):
                sinal = "🔴 VENDA CONFIRMADA (SMC + IFR)"
                sl = preco_atual + 3.50
                tp = preco_atual - 7.00
                explicacao = (
                    f"🎯 *SINAL DE ALTA FIDELIDADE (VENDA)*\n\n"
                    f"📌 *Preço Entrada:* ${preco_atual:.2f}\n"
                    f"🎯 *Take Profit:* ${tp:.2f} (-7.00)\n"
                    f"🛡️ *Stop Loss:* ${sl:.2f} (+3.50)\n"
                    f"📊 *IFR (RSI):* {rsi_atual:.1f} (Ideal: 35-45)\n"
                    f"📉 *BOS:* Fundo rompido em ${fundo_smc:.2f}\n\n"
                    f"💡 *Confluência:* Tendência + Rompimento Estrutural + Impulso IFR."
                )

    # Se não houver alinhamento perfeito de todas as confluências, não envia o sinal no Telegram
    if sinal is None:
        print(f"-> Nenhuma confluência perfeita encontrada no momento (Preço: ${preco_atual:.2f} | RSI: {rsi_atual:.1f} | SMC: {evento_smc}). Envio cancelado.")
        return f"Sem sinal perfeito. Preço: {preco_atual:.2f}, RSI: {rsi_atual:.1f}, SMC: {evento_smc}"

    # Visual do Gráfico
    mc = mpf.make_marketcolors(
        up='#00e676', down='#ff5252',
        edge={'up': '#00e676', 'down': '#ff5252'},
        wick={'up': '#00e676', 'down': '#ff5252'},
        volume='in'
    )
    
    style_custom = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor='#121824',
        edgecolor='#1f293d',
        figcolor='#0d1117',
        gridcolor='#1f293d',
        gridstyle='--',
        rc={'font.family': 'sans-serif', 'font.size': 9}
    )

    add_plots = [
        mpf.make_addplot(df_recorte['EMA9'].tail(45), color='#00b0ff', width=1.8),
        mpf.make_addplot(df_recorte['EMA21'].tail(45), color='#ffd600', width=1.8)
    ]

    df_plot = df_recorte.tail(45)
    linhas_h = [preco_atual, preco_atual+7.0, preco_atual-3.5] if "COMPRA" in sinal else [preco_atual, preco_atual-7.0, preco_atual+3.5]
    cores_linhas = ['#ffd600', '#00e676', '#ff5252']

    caminho_imagem = "grafico_aula.png"
    
    fig, axes = mpf.plot(
        df_plot,
        type='candle',
        style=style_custom,
        addplot=add_plots,
        title=dict(title=f"  XAU/USD SPOT (M15)  |  SINAL VALIDADO", color='#ffffff', fontsize=11, weight='bold'),
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
        f"🎯 *Sinal:* {sinal}\n\n"
        f"{explicacao}"
    )
    
    print("-> Confluência confirmada! Enviando alerta para o Telegram...")
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
        return f"<h1>Resultado da Análise:</h1><pre>{resposta}</pre>"
    except Exception as e:
        return f"<h1>Erro ao Executar:</h1><pre>{str(e)}</pre>"

def loop_monitoramento():
    print("-> Monitoramento estrito ativado.")
    time.sleep(5)
    while True:
        try:
            executar_analise_e_envio()
        except Exception as e:
            print(f"❌ Erro na execução: {e}")
        
        time.sleep(300)

if __name__ == "__main__":
    t = threading.Thread(target=loop_monitoramento)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
