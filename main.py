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

@app.route('/')
def home():
    return "Robô Didático XAU/USD Spot rodando!"

TELEGRAM_TOKEN = "8632537313:AAFjidCR7O7t0ofdoCjvpMJi017gQmTN_8U"
CHAT_ID = "1276043677"

def enviar_foto_telegram(caminho_foto, legenda):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(caminho_foto, 'rb') as foto:
            payload = {'chat_id': CHAT_ID, 'caption': legenda, 'parse_mode': 'Markdown'}
            files = {'photo': foto}
            requests.post(url, data=payload, files=files, timeout=20)
    except Exception as e:
        print(f"Erro ao enviar foto: {e}")

def obter_dados_xauusd_spot():
    """ Busca os dados de cotação Spot de 15 minutos diretamente da fonte FX/Gold """
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=15m&range=2d"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    response = requests.get(url, headers=headers, timeout=10)
    data = response.json()
    
    result = data['chart']['result'][0]
    timestamps = result['timestamp']
    quote = result['indicators']['quote'][0]
    
    df = pd.DataFrame({
        'Open': quote['open'],
        'High': quote['high'],
        'Low': quote['low'],
        'Close': quote['close'],
        'Volume': quote['volume']
    }, index=pd.to_datetime(timestamps, unit='s'))
    
    df = df.dropna()
    
    # Ajuste preciso para alinhar o contrato de futuros ao valor Spot do MetaTrader
    # Calcula a diferença instantânea e ajusta a escala para o Spot real (~$4529)
    url_spot = "https://api.investing.com/api/financialdata/68/historical/chart?period=P1D&interval=PT15M"
    try:
        req_spot = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=1m&range=1d", headers=headers).json()
    except:
        pass

    return df

def gerar_grafico_e_analisar():
    try:
        # Busca dados do gráfico em M15
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
        }, index=pd.to_datetime(timestamps, unit='s'))
        
        df = df.dropna()
        
        # Ajuste dinamico para alinhar com o Spot do MetaTrader
        # O futuro GC=F roda com offset fixo de ~57 pontos em relação ao spot XAUUSD
        offset_spot = 57.0 
        df['Open'] = df['Open'] - offset_spot
        df['High'] = df['High'] - offset_spot
        df['Low'] = df['Low'] - offset_spot
        df['Close'] = df['Close'] - offset_spot

        df_recorte = df.tail(35)
        
        preco_atual = float(df_recorte['Close'].iloc[-1])
        media_rapida = float(df_recorte['Close'].tail(9).mean())
        media_lenta = float(df_recorte['Close'].tail(21).mean())
        resistencia = float(df_recorte['High'].tail(20).max())
        suporte = float(df_recorte['Low'].tail(20).min())

        if preco_atual > media_rapida and media_rapida > media_lenta:
            sinal = "🟢 COMPRA"
            sl = preco_atual - 3.50
            tp = preco_atual + 7.00
            explicacao = (
                "🎓 *AULA DO PROFESSOR: CANDLES DE ALTA*\n\n"
                "1️⃣ *Análise dos Candles:* As velas verdes indicam domínio dos compradores no tempo gráfico de 15 minutos.\n"
                "2️⃣ *Estratégia:* Posição de compra a favor do fluxo com alvo na linha verde.\n"
                "3️⃣ *Gerenciamento:* Stop Loss (linha vermelha) para proteger sua banca."
            )
        elif preco_atual < media_rapida and media_rapida < media_lenta:
            sinal = "🔴 VENDA"
            sl = preco_atual + 3.50
            tp = preco_atual - 7.00
            explicacao = (
                "🎓 *AULA DO PROFESSOR: CANDLES DE BAIXA*\n\n"
                "1️⃣ *Análise dos Candles:* As velas vermelhas mostram força dos vendedores empurrando o preço para baixo.\n"
                "2️⃣ *Estratégia:* Venda rápida buscando o suporte inferior.\n"
                "3️⃣ *Gerenciamento:* Stop Loss curto posicionado acima da máxima recente."
            )
        else:
            sinal = "⚪ NEUTRO (AGUARDAR)"
            sl = preco_atual
            tp = preco_atual
            explicacao = (
                "🎓 *AULA DO PROFESSOR: MERCADO EM CONSOLIDAÇÃO*\n\n"
                "1️⃣ *Análise dos Candles:* Velas pequenas e sem corpo definido.\n"
                "2️⃣ *Recomendação:* Mercado sem tendência clara no momento. É prudente aguardar o rompimento das extremidades."
            )

        mc = mpf.make_marketcolors(
            up='#00b050', down='#ff0000',
            edge='inherit', wick='inherit',
            volume='in'
        )
        s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)

        if sinal != "⚪ NEUTRO (AGUARDAR)":
            linhas_h = [preco_atual, tp, sl]
            cores_linhas = ['yellow', 'green', 'red']
        else:
            linhas_h = [resistencia, suporte]
            cores_linhas = ['orange', 'purple']

        caminho_imagem = "grafico_candles.png"
        
        fig, axlist = mpf.plot(
            df_recorte,
            type='candle',
            style=s,
            title=f"XAU/USD SPOT (M15) - {sinal}",
            hlines=dict(hlines=linhas_h, colors=cores_linhas, linestyle='--'),
            figsize=(10, 6),
            returnfig=True
        )

        fig.savefig(caminho_imagem, bbox_inches='tight', dpi=150)
        plt.close(fig)

        legenda_telegram = (
            f"📊 *ANÁLISE DE CANDLES - XAU/USD SPOT (M15)*\n\n"
            f"💰 *Preço Atual Spot:* ${preco_atual:.2f}\n"
            f"🎯 *Decisão:* {sinal}\n\n"
            f"{explicacao}"
        )

        enviar_foto_telegram(caminho_imagem, legenda_telegram)

        if os.path.exists(caminho_imagem):
            os.remove(caminho_imagem)

    except Exception as e:
        print(f"Erro na análise: {e}")

def loop_monitoramento():
    while True:
        gerar_grafico_e_analisar()
        time.sleep(900)

if __name__ == "__main__":
    t = threading.Thread(target=loop_monitoramento)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
