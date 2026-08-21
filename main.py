import time
import requests
import yfinance as yf

# --- CONFIGURAÇÕES DO USUÁRIO ---
TELEGRAM_TOKEN = "8632537313:AAFjidCR7O7t0ofdoCjvpMJi017gQmTN_8U"
CHAT_ID = "1276043677"

# Armazena o último sinal para evitar repetição contínua da mesma ordem
ultimo_sinal = None 

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    dados = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    requests.post(url, data=dados)

def analisar_xauusd():
    global ultimo_sinal
    
    # Puxa os dados M15 do Ouro
    gold = yf.Ticker("GC=F")
    df = gold.history(period="2d", interval="15m")
    
    if df.empty or len(df) < 20:
        return
    
    # 1. Indicador: Média Móvel (SMA 20)
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    
    # 2. Indicador: RSI 14
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Preços e Indicadores do último candle fechado
    preco_atual = df['Close'].iloc[-1]
    media_atual = df['SMA20'].iloc[-1]
    rsi_atual = df['RSI'].iloc[-1]
    
    # --- LÓGICA DE SINAIS DE ALTA PROBABILIDADE ---
    
    # CONDIÇÃO DE COMPRA: Preço acima da Média + RSI entre 52 e 68 (força compradora sem estar exausta)
    if preco_atual > media_atual and 52 <= rsi_atual < 70:
        if ultimo_sinal != "COMPRA":
            ultimo_sinal = "COMPRA"
            
            # Cálculo didático de SL/TP (Estimativa de $5 a $8 no Ouro)
            sl = preco_atual - 5.00
            tp = preco_atual + 7.50
            
            msg = (
                f"🟢 *SINAL DE COMPRA (XAU/USD)* 🟢\n\n"
                f"🎯 *Entrada sugerida:* ${preco_atual:.2f}\n"
                f"🛑 *Stop Loss (SL):* ${sl:.2f}\n"
                f"🎯 *Take Profit (TP):* ${tp:.2f}\n\n"
                f"📊 *Indicadores no M15:*\n"
                f"• Preço acima da SMA20 (${media_atual:.2f})\n"
                f"• RSI forte em {rsi_atual:.1f}\n\n"
                f"📚 *Aula Rápida:* O preço está alinhado com a média e o RSI confirma momento comprador. "
                f"Abra o gráfico e verifique se não há resistência forte logo acima!"
            )
            enviar_telegram(msg)
            
    # CONDIÇÃO DE VENDA: Preço abaixo da Média + RSI entre 32 e 48 (força vendedora sem estar exausta)
    elif preco_atual < media_atual and 30 < rsi_atual <= 48:
        if ultimo_sinal != "VENDA":
            ultimo_sinal = "VENDA"
            
            sl = preco_atual + 5.00
            tp = preco_atual - 7.50
            
            msg = (
                f"🔴 *SINAL DE VENDA (XAU/USD)* 🔴\n\n"
                f"🎯 *Entrada sugerida:* ${preco_atual:.2f}\n"
                f"🛑 *Stop Loss (SL):* ${sl:.2f}\n"
                f"🎯 *Take Profit (TP):* ${tp:.2f}\n\n"
                f"📊 *Indicadores no M15:*\n"
                f"• Preço abaixo da SMA20 (${media_atual:.2f})\n"
                f"• RSI fraco em {rsi_atual:.1f}\n\n"
                f"📚 *Aula Rápida:* Vendedores estão pressionando o mercado para baixo. "
                f"Verifique no gráfico se há um suporte próximo antes de abrir a ordem."
            )
            enviar_telegram(msg)
            
    else:
        # Se os dois indicadores não concordarem, o bot fica neutro
        if ultimo_sinal != "NEUTRO":
            ultimo_sinal = "NEUTRO"

# Envia mensagem inicial ao ligar
enviar_telegram("🤖 *SISTEMA DE SINAIS E AULAS ATIVADO!*\nMonitorando XAU/USD no M15...")

# Executa imediatamente a primeira checagem
analisar_xauusd()

# Loop contínuo a cada 5 minutos
try:
    while True:
        analisar_xauusd()
        time.sleep(300) # Checa a cada 5 minutos (300 segundos)
except KeyboardInterrupt:
    print("Monitor finalizado.")
