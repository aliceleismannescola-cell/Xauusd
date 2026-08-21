import os
import time
import requests
import yfinance as yf

# CONFIGURAÇÕES DO TELEGRAM
TELEGRAM_TOKEN = "8632537313:AAFjidCR7O7t0ofdoCjvpMJi017gQmTN_8U"
CHAT_ID = "1276043677"

def enviar_mensagem_telegram(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

def analisar_xauusd():
    try:
        # Baixa os últimos dados do Ouro em M15
        dados = yf.download(tickers="GC=F", period="5d", interval="15m", progress=False)
        
        if dados.empty or len(dados) < 20:
            return None

        # Trata os dados caso venham com MultiIndex
        if hasattr(dados.columns, 'levels'):
            close = dados['Close']['GC=F']
            high = dados['High']['GC=F']
            low = dados['Low']['GC=F']
        else:
            close = dados['Close']
            high = dados['High']
            low = dados['Low']

        preco_atual = float(close.iloc[-1])
        media_rapida = float(close.tail(9).mean())   # Média de 9 períodos
        media_lenta = float(close.tail(21).mean())   # Média de 21 períodos
        
        # Suporte e Resistência recentes
        resistencia = float(high.tail(20).max())
        suporte = float(low.tail(20).min())

        # Lógica de Sinal para Day Trade (M15)
        if preco_atual > media_rapida and media_rapida > media_lenta:
            sinal = "🟢 *SINAL DE COMPRA (DAY TRADE)*"
            sl = preco_atual - 3.50  # SL estimado de ~35 pips
            tp = preco_atual + 7.00  # TP estimado de ~70 pips (Risco:Retorno 1:2)
            dica = "Tendência de alta no M15. O preço está trabalhando acima das médias móveis. Procure gatilhos de compra próximo ao suporte."
        elif preco_atual < media_rapida and media_rapida < media_lenta:
            sinal = "🔴 *SINAL DE VENDA (DAY TRADE)*"
            sl = preco_atual + 3.50  # SL estimado de ~35 pips
            tp = preco_atual - 7.00  # TP estimado de ~70 pips (Risco:Retorno 1:2)
            dica = "Tendência de baixa no M15. O preço está trabalhando abaixo das médias móveis. Procure gatilhos de venda próximo à resistência."
        else:
            sinal = "⚪ *NEUTRO / AGUARDAR*"
            sl = preco_atual
            tp = preco_atual
            dica = "Mercado lateral no M15 sem direção definida. Aguarde uma confirmação de rompimento antes de abrir posição."

        mensagem = (
            f"⚡ *ALERTA DAY TRADE - XAU/USD (M15)* ⚡\n\n"
            f"💰 *Preço Atual:* ${preco_atual:.2f}\n"
            f"📊 *Sinal:* {sinal}\n\n"
            f"🎯 *Alvos Sugeridos (M15):*\n"
            f"▪️ *Entrada:* ${preco_atual:.2f}\n"
            f"▪️ *Stop Loss (SL):* ${sl:.2f}\n"
            f"▪️ *Take Profit (TP):* ${tp:.2f}\n\n"
            f"📌 *Níveis Importantes:*\n"
            f"📈 Resistência: ${resistencia:.2f}\n"
            f"📉 Suporte: ${suporte:.2f}\n\n"
            f"💡 *Dica Operacional:*\n{dica}"
        )

        return mensagem

    except Exception as e:
        print(f"Erro na analise: {e}")
        return None

def main():
    enviar_mensagem_telegram("🤖 *Robô de Day Trade XAU/USD Atualizado!* \nMonitorando gráfico de M15 a cada 15 minutos.")
    
    while True:
        mensagem = analisar_xauusd()
        if mensagem:
            enviar_mensagem_telegram(mensagem)
        
        # Aguarda 15 minutos (900 segundos) para a próxima verificação
        time.sleep(900)

if __name__ == "__main__":
    main()
