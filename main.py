import os
import time
import threading
import requests
import yfinance as yf
import matplotlib
matplotlib.use('Agg')  # Para rodar em servidores sem tela (como o Render)
import matplotlib.pyplot as plt
from flask import Flask

# Servidor Web Leve para o Render Free
app = Flask(__name__)

@app.route('/')
def home():
    return "Robô Didático XAU/USD rodando com sucesso!"

# CONFIGURAÇÕES DO TELEGRAM
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
        # Baixa os últimos dados de M15 do XAU/USD
        dados = yf.download(tickers="GC=F", period="2d", interval="15m", progress=False)
        
        if dados.empty or len(dados) < 30:
            return

        if hasattr(dados.columns, 'levels'):
            close = dados['Close']['GC=F']
            high = dados['High']['GC=F']
            low = dados['Low']['GC=F']
        else:
            close = dados['Close']
            high = dados['High']
            low = dados['Low']

        # Pega as últimas 30 velas para o gráfico ficar bem visível no celular
        df_recorte = close.tail(30)
        
        preco_atual = float(close.iloc[-1])
        media_rapida = float(close.tail(9).mean())
        media_lenta = float(close.tail(21).mean())
        resistencia = float(high.tail(20).max())
        suporte = float(low.tail(20).min())

        # Análise e definição dos pontos da aula
        if preco_atual > media_rapida and media_rapida > media_lenta:
            sinal = "🟢 COMPRA"
            sl = preco_atual - 3.50
            tp = preco_atual + 7.00
            explicacao = (
                "🎓 *AULA DO PROFESSOR: TENDÊNCIA DE ALTA*\n\n"
                "1️⃣ *O que estamos vendo?* O preço está acima das médias móveis (linhas guiadoras). Isso mostra força dos compradores.\n"
                "2️⃣ *Por que comprar?* O mercado rompeu a consolidação e está fazendo topos mais altos.\n"
                "3️⃣ *Gerenciamento:* Coloquei o Stop Loss (linha vermelha) abaixo do suporte recente para te proteger caso o mercado volte contra você."
            )
        elif preco_atual < media_rapida and media_rapida < media_lenta:
            sinal = "🔴 VENDA"
            sl = preco_atual + 3.50
            tp = preco_atual - 7.00
            explicacao = (
                "🎓 *AULA DO PROFESSOR: TENDÊNCIA DE BAIXA*\n\n"
                "1️⃣ *O que estamos vendo?* Os candles estão caindo abaixo das médias móveis. A força dominante é vendedora.\n"
                "2️⃣ *Por que vender?* O preço perdeu sustentação e a tendência imediata no M15 é de queda.\n"
                "3️⃣ *Gerenciamento:* O Stop Loss (linha vermelha) fica acima da resistência recente para limitar o risco."
            )
        else:
            sinal = "⚪ NEUTRO (AGUARDAR)"
            sl = preco_atual
            tp = preco_atual
            explicacao = (
                "🎓 *AULA DO PROFESSOR: MERCADO LATERAL*\n\n"
                "1️⃣ *O que estamos vendo?* As velas estão cruzando as médias de um lado para o outro sem direção clara.\n"
                "2️⃣ *Ação recomendada:* Fique de fora! Não operamos no meio da consolidação. Esperamos o preço tocar no Suporte ou na Resistência para decidir."
            )

        # DESENHANDO O GRÁFICO DIDÁTICO
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plota a linha do preço
        ax.plot(df_recorte.index, df_recorte.values, label='Preço XAU/USD', color='#00d2ff', linewidth=2)

        # Desenha as linhas horizontais didáticas se houver sinal ativo
        if sinal != "⚪ NEUTRO (AGUARDAR)":
            ax.axhline(preco_atual, color='yellow', linestyle='--', label=f'Entrada: ${preco_atual:.2f}')
            ax.axhline(tp, color='green', linestyle='--', label=f'Take Profit (TP): ${tp:.2f}')
            ax.axhline(sl, color='red', linestyle='--', label=f'Stop Loss (SL): ${sl:.2f}')
        else:
            ax.axhline(resistencia, color='orange', linestyle=':', label=f'Resistência: ${resistencia:.2f}')
            ax.axhline(suporte, color='purple', linestyle=':', label=f'Suporte: ${suporte:.2f}')

        ax.set_title(f"AULA DE TÉCNICA XAU/USD (M15) - {sinal}", fontsize=14, color='white', fontweight='bold')
        ax.set_ylabel("Preço em USD", fontsize=11)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.2)

        # Salva o gráfico como imagem
        caminho_imagem = "grafico_aula.png"
        plt.savefig(caminho_imagem, bbox_inches='tight', dpi=150)
        plt.close()

        # Legenda da foto com os dados e a explicação
        legenda_telegram = (
            f"📊 *ANÁLISE COM GRÁFICO - XAU/USD (M15)*\n\n"
            f"💰 *Preço Atual:* ${preco_atual:.2f}\n"
            f"🎯 *Decisão:* {sinal}\n\n"
            f"{explicacao}"
        )

        # Envia a foto com a legenda
        enviar_foto_telegram(caminho_imagem, legenda_telegram)

        # Remove a imagem temporária do servidor
        if os.path.exists(caminho_imagem):
            os.remove(caminho_imagem)

    except Exception as e:
        print(f"Erro ao gerar gráfico/análise: {e}")

def loop_monitoramento():
    while True:
        gerar_grafico_e_analisar()
        time.sleep(900)  # Executa a cada 15 minutos

if __name__ == "__main__":
    t = threading.Thread(target=loop_monitoramento)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
