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
    return "Robô Didático Avançado XAU/USD Spot rodando!"

TELEGRAM_TOKEN = "8632537313:AAFjidCR7O7t0ofdoCjvpMJi017gQmTN_8U"
CHAT_ID = "1276043677"

def enviar_foto_telegram(caminho_foto, legenda):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(caminho_foto, 'rb') as foto:
            payload = {'chat_id': CHAT_ID, 'caption': legenda, 'parse_mode': 'Markdown'}
            files = {'photo': foto}
            res = requests.post(url, data=payload, files=files, timeout=25)
            print("Resposta do Telegram:", res.status_code)
    except Exception as e:
        print(f"Erro ao enviar foto: {e}")

def gerar_grafico_e_analisar():
    try:
        print("Buscando dados e gerando gráfico...")
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=15m&range=2d"
        headers = {'User-Agent': 'Mozilla/5.0'}
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
        
        # Ajuste de cotação para o Spot XAUUSD exato
        offset_spot = 57.0 
        df['Open'] = df['Open'] - offset_spot
        df['High'] = df['High'] - offset_spot
        df['Low'] = df['Low'] - offset_spot
        df['Close'] = df['Close'] - offset_spot

        df_recorte = df.tail(35).copy()
        
        # Cálculo dos Indicadores para o gráfico
        df_recorte['EMA9'] = df_recorte['Close'].ewm(span=9, adjust=False).mean()
        df_recorte['EMA21'] = df_recorte['Close'].ewm(span=21, adjust=False).mean()

        preco_atual = float(df_recorte['Close'].iloc[-1])
        ema9_atual = float(df_recorte['EMA9'].iloc[-1])
        ema21_atual = float(df_recorte['EMA21'].iloc[-1])
        resistencia = float(df_recorte['High'].tail(20).max())
        suporte = float(df_recorte['Low'].tail(20).min())

        # Análise didática completa
        if preco_atual > ema9_atual and ema9_atual > ema21_atual:
            sinal = "🟢 COMPRA (ALTA)"
            sl = preco_atual - 3.50
            tp = preco_atual + 7.00
            rr = "1 : 2.0 (Excelente)"
            explicacao = (
                "🎓 *AULA COMPLETA DO PROFESSOR: TENDÊNCIA DE ALTA*\n\n"
                "📌 *1. Padrão de Candles & Estrutura:* Os últimos candles estão renovando máximas acima da EMA 9. Notamos rejeição de baixa nos pavios inferiores (força dos compradores).\n\n"
                "📌 *2. Médias Móveis (EMA 9 x EMA 21):* A média rápida azul (EMA 9) cruzou para cima da média amarela (EMA 21). Isso indica alinhamento do fluxo comprador em M15.\n\n"
                "📌 *3. Plano de Trade (Gatilho):*\n"
                f"   • *Entrada:* ${preco_atual:.2f} (Preço de Mercado)\n"
                f"   • *Take Profit (Linha Verde):* ${tp:.2f} (+70 pips / $7.00)\n"
                f"   • *Stop Loss (Linha Vermelha):* ${sl:.2f} (-35 pips / $3.50)\n"
                f"   • *Relação Risco/Retorno:* {rr}\n\n"
                "💡 *Dica do Professor:* Se o preço retornar para testar a linha azul da EMA 9 sem romper para baixo, é uma excelente oportunidade para buscar a confirmação da compra."
            )
        elif preco_atual < ema9_atual and ema9_atual < ema21_atual:
            sinal = "🔴 VENDA (BAIXA)"
            sl = preco_atual + 3.50
            tp = preco_atual - 7.00
            rr = "1 : 2.0 (Excelente)"
            explicacao = (
                "🎓 *AULA COMPLETA DO PROFESSOR: TENDÊNCIA DE BAIXA*\n\n"
                "📌 *1. Padrão de Candles & Estrutura:* Velas vermelhas fortes com fechamentos próximos das mínimas. Vendedores no controle do preço.\n\n"
                "📌 *2. Médias Móveis (EMA 9 x EMA 21):* A EMA 9 azul trabalha inclinada para baixo, distante da EMA 21 amarela, confirmando impulso vendedor contínuo.\n\n"
                "📌 *3. Plano de Trade (Gatilho):*\n"
                f"   • *Entrada:* ${preco_atual:.2f} (Preço de Mercado)\n"
                f"   • *Take Profit (Linha Verde):* ${tp:.2f} (+70 pips / $7.00)\n"
                f"   • *Stop Loss (Linha Vermelha):* ${sl:.2f} (-35 pips / $3.50)\n"
                f"   • *Relação Risco/Retorno:* {rr}\n\n"
                "💡 *Dica do Professor:* Mantenha sua ordem de Stop acionada. Caso ocorra um pullback de alta em direção à EMA 9, observe se haverá rejeição para manter a posição."
            )
        else:
            sinal = "⚪ NEUTRO (CONSOLIDAÇÃO)"
            sl = preco_atual
            tp = preco_atual
            rr = "Indefinida"
            explicacao = (
                "🎓 *AULA COMPLETA DO PROFESSOR: CONSOLIDAÇÃO / LATERALIZAÇÃO*\n\n"
                "📌 *1. Padrão de Candles & Estrutura:* Candles pequenos, dojis e corpos entrelaçados. Mercado sem volume definido no momento.\n\n"
                "📌 *2. Médias Móveis (EMA 9 x EMA 21):* As médias móveis estão 'comendo de lado' (horizontais e sobrepostas ao preço). Isso sinaliza falta de direção clara.\n\n"
                "📌 *3. Zonas Chave de Decisão:*\n"
                f"   • *Resistência Superior (Linha Laranja):* ${resistencia:.2f}\n"
                f"   • *Suporte Inferior (Linha Roxa):* ${suporte:.2f}\n\n"
                "💡 *Dica do Professor:* Paciência é uma virtude no trading! Não force operações dentro da consolidação. Espere uma vela de 15 minutos FECHAR fora dessa zona para confirmar o rompimento."
            )

        mc = mpf.make_marketcolors(
            up='#00e676', down='#ff5252',
            edge='inherit', wick='inherit',
            volume='in'
        )
        s = mpf.make_mpf_style(
            base_mpf_style='nightclouds', 
            marketcolors=mc,
            gridstyle=':',
            gridcolor='#333333'
        )

        add_plots = [
            mpf.makeaddplot(df_recorte['EMA9'], color='#00b0ff', width=1.5),
            mpf.makeaddplot(df_recorte['EMA21'], color='#ffd600', width=1.5)
        ]

        if "COMPRA" in sinal or "VENDA" in sinal:
            linhas_h = [preco_atual, tp, sl]
            cores_linhas = ['#ffea00', '#00e676', '#ff1744']
        else:
            linhas_h = [resistencia, suporte]
            cores_linhas = ['#ff9100', '#e040fb']

        caminho_imagem = "grafico_aula_detalhada.png"
        
        fig, axlist = mpf.plot(
            df_recorte,
            type='candle',
            style=s,
            addplot=add_plots,
            title=f"\n XAU/USD SPOT (M15) - AULA DE ANÁLISE TÉCNICA [{sinal}]",
            hlines=dict(hlines=linhas_h, colors=cores_linhas, linestyle='-.', linewidths=1.2),
            figsize=(11, 6.5),
            returnfig=True
        )

        ax = axlist[0]
        ax.text(0.02, 0.93, "— EMA 9 (Média Rápida - Azul)\n— EMA 21 (Média Lenta - Amarela)", 
                transform=ax.transAxes, color='white', fontsize=9, 
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#1e1e1e', alpha=0.8, edgecolor='#555555'))

        ax.annotate(f'Preço: ${preco_atual:.2f}', 
                    xy=(len(df_recorte)-1, preco_atual), 
                    xytext=(len(df_recorte)-8, preco_atual + 1.5),
                    arrowprops=dict(facecolor='yellow', shrink=0.05, width=1, headwidth=6),
                    color='yellow', fontweight='bold', fontsize=9,
                    bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

        fig.savefig(caminho_imagem, bbox_inches='tight', dpi=180)
        plt.close(fig)

        legenda_telegram = (
            f"📊 *ESTUDO TÉCNICO COMPLETO - XAU/USD (M15)*\n\n"
            f"💵 *Cotação Spot Atual:* ${preco_atual:.2f}\n"
            f"🎯 *Análise Técnica:* {sinal}\n\n"
            f"{explicacao}"
        )

        enviar_foto_telegram(caminho_imagem, legenda_telegram)

        if os.path.exists(caminho_imagem):
            os.remove(caminho_imagem)

    except Exception as e:
        print(f"Erro na análise avançada: {e}")

def loop_monitoramento():
    # Envia IMEDIATAMENTE a primeira mensagem ao ligar
    gerar_grafico_e_analisar()
    
    while True:
        time.sleep(900)
        gerar_grafico_e_analisar()

if __name__ == "__main__":
    t = threading.Thread(target=loop_monitoramento)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
