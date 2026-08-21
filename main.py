import os
import time
import threading
import requests
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Robô Didático XAU/USD rodando!"

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

def gerar_grafico_e_analisar():
    try:
        dados = yf.download(tickers="GC=F", period="2d", interval="15m", progress=False)
        
        if dados.empty or len(dados) < 30:
            return

        # Ajusta estrutura dos dados do yfinance
        if isinstance(dados.columns, pd.MultiIndex):
            df = pd.DataFrame({
                'Open': dados['Open']['GC=F'],
                'High': dados['High']['GC=F'],
                'Low': dados['Low']['GC=F'],
                'Close': dados['Close']['GC=F'],
                'Volume': dados['Volume']['GC=F']
            })
        else:
            df = dados[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

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
                "1️⃣ *Análise dos Candles:* As velas verdes mostram pressão dos compradores empurrando o preço para cima.\n"
                "2️⃣ *Gatilho de Entrada:* Comprar próximo ao preço atual com foco no movimento do M15.\n"
                "3️⃣ *Proteção:* Stop Loss na linha vermelha para conter perdas e Take Profit na linha verde."
            )
        elif preco_atual < media_rapida and media_rapida < media_lenta:
            sinal = "🔴 VENDA"
            sl = preco_atual + 3.50
            tp = preco_atual - 7.00
            explicacao = (
                "🎓 *AULA DO PROFESSOR: CANDLES DE BAIXA*\n\n"
                "1️⃣ *Análise dos Candles:* As velas vermelhas mostram a força vendedora dominando as últimas barras.\n"
                "2️⃣ *Gatilho de Entrada:* Oportunidade de venda a favor da tendência imediata.\n"
                "3️⃣ *Proteção:* Stop Loss posicionado acima da resistência e Take Profit no alvo abaixo."
            )
        else:
            sinal = "⚪ NEUTRO (AGUARDAR)"
            sl = preco_atual
            tp = preco_atual
            explicacao = (
                "🎓 *AULA DO PROFESSOR: MERCADO EM CONSOLIDAÇÃO*\n\n"
                "1️⃣ *Análise dos Candles:* As velas estão alternando entre verde e vermelho sem sair do lugar.\n"
                "2️⃣ *Recomendação:* Aguarde um candle de força (corpo grande) romper o Suporte ou a Resistência."
            )

        # Configuração do Estilo de Candlesticks Profissional
        mc = mpf.make_marketcolors(
            up='#00b050', down='#ff0000',
            edge='inherit', wick='inherit',
            volume='in'
        )
        s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)

        # Adiciona as linhas horizontais de entrada, SL e TP
        linhas_h = []
        if sinal != "⚪ NEUTRO (AGUARDAR)":
            linhas_h = [preco_atual, tp, sl]
            cores_linhas = ['yellow', 'green', 'red']
        else:
            linhas_h = [resistencia, suporte]
            cores_linhas = ['orange', 'purple']

        caminho_imagem = "grafico_candles.png"
        
        # Desenha o gráfico de velas
        fig, axlist = mpf.plot(
            df_recorte,
            type='candle',
            style=s,
            title=f"XAU/USD (M15) - {sinal}",
            hlines=dict(hlines=linhas_h, colors=cores_linhas, linestyle='--'),
            figsize=(10, 6),
            returnfig=True
        )

        fig.savefig(caminho_imagem, bbox_inches='tight', dpi=150)
        plt.close(fig)

        legenda_telegram = (
            f"📊 *ANÁLISE DE CANDLES - XAU/USD (M15)*\n\n"
            f"💰 *Preço Atual:* ${preco_atual:.2f}\n"
            f"🎯 *Decisão:* {sinal}\n\n"
            f"{explicacao}"
        )

        enviar_foto_telegram(caminho_imagem, legenda_telegram)

        if os.path.exists(caminho_imagem):
            os.remove(caminho_imagem)

    except Exception as e:
        print(f"Erro ao gerar gráfico de candles: {e}")

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
