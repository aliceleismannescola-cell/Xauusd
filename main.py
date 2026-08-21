import os
import requests
import pandas as pd
import numpy as np
from flask import Flask, request
from tvdatafeed import TvDatafeed, Interval

app = Flask(__name__)

# Configurações do Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "SEU_TOKEN_AQUI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "SEU_CHAT_ID_AQUI")

def obter_dados_xauusd():
    """Busca os dados do Ouro Spot (XAUUSD) via OANDA no TradingView para alinhar com a Exness"""
    try:
        tv = TvDatafeed()
        # Busca os últimos 100 candles de M15 do XAUUSD na OANDA
        df = tv.get_hist(symbol='XAUUSD', exchange='OANDA', interval=Interval.in_15_minute, n_bars=100)
        
        if df is None or df.empty:
            return None
        
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        return df
    except Exception as e:
        print(f"Erro ao buscar dados do Spot Gold: {e}")
        return None

def calcular_rsi(df, period=14):
    """Calcula o IFR / RSI clássico de 14 períodos"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def calcular_indicadores(df):
    """Calcula as Médias Móveis EmA 9 e EMA 21"""
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df = calcular_rsi(df)
    return df

def enviar_mensagem_telegram(texto):
    """Envia o alerta técnico para o canal do Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao enviar mensagem no Telegram: {e}")
        return False

def executar_analise_e_envio():
    """Executa a checagem dos 4 critérios de entrada perfeita"""
    df = obter_dados_xauusd()
    if df is None or len(df) < 30:
        return "Erro ao obter dados atualizados do mercado."

    df = calcular_indicadores(df)
    
    # Dados da última vela fechada
    atual = df.iloc[-1]
    anterior = df.iloc[-2]
    
    preco = round(atual['Close'], 2)
    rsi = round(atual['RSI'], 2)
    ema9 = atual['EMA9']
    ema21 = atual['EMA21']
    
    # Identificação de BOS e Rejeição
    topo_anterior = df['High'].iloc[-15:-2].max()
    fundo_anterior = df['Low'].iloc[-15:-2].min()
    
    bos_alta = atual['Close'] > topo_anterior
    bos_baixa = atual['Close'] < fundo_anterior
    
    tamanho_corpo = abs(atual['Close'] - atual['Open'])
    pavio_superior = atual['High'] - max(atual['Close'], atual['Open'])
    pavio_inferior = min(atual['Close'], atual['Open']) - atual['Low']
    
    rejeicao_alta = pavio_superior > (tamanho_corpo * 1.5)
    rejeicao_baixa = pavio_inferior > (tamanho_corpo * 1.5)
    
    sinal = None
    
    # Validação de COMPRA
    if (ema9 > ema21) and (preco > ema9) and (55.0 <= rsi <= 65.0) and bos_alta and not rejeicao_alta:
        sinal = "COMPRA 🟢"
        sl = round(atual['Low'] - 1.50, 2)
        tp = round(preco + ((preco - sl) * 2), 2)
        
    # Validação de VENDA
    elif (ema9 < ema21) and (preco < ema9) and (35.0 <= rsi <= 45.0) and bos_baixa and not rejeicao_baixa:
        sinal = "VENDA 🔴"
        sl = round(atual['High'] + 1.50, 2)
        tp = round(preco - ((sl - preco) * 2), 2)

    if sinal:
        mensagem = (
            f"🎯 *SINAL CONFIRMADO - XAU/USD (M15)*\n\n"
            f"📍 *Ação:* {sinal}\n"
            f"💰 *Preço Atual (Exness/Spot):* ${preco}\n"
            f"📊 *RSI (14):* {rsi}\n\n"
            f"🛑 *Stop Loss:* ${sl}\n"
            f"🎯 *Take Profit:* ${tp}\n\n"
            f"⚠️ _Gerencie seu risco adequadamente._"
        )
        enviar_mensagem_telegram(mensagem)
        return f"Sinal de {sinal} enviado para o Telegram com sucesso!"
    
    estado_smc = "BOS ALTA" if bos_alta else ("BOS BAIXA" if bos_baixa else "CONSOLIDAÇÃO")
    return f"Sem sinal perfeito. Preço Spot: {preco}, RSI: {rsi}, SMC: {estado_smc}"

@app.route('/')
def home():
    return "Servidor do Robô de Ouro está Online!"

@app.route('/enviar', methods=['GET', 'HEAD'])
def enviar_manual():
    try:
        resposta = executar_analise_e_envio()
        return f"<h1>Resultado da Análise:</h1><pre>{resposta}</pre>"
    except Exception as e:
        return f"<h1>Erro ao Executar:</h1><pre>{str(e)}</pre>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
