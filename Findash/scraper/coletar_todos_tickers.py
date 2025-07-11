import os
import json
import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright
from extrair_dados import extrair_dados_ticker

def carregar_tickers(caminho_csv="Findash/docs/acoes-listadas-b3.csv"):
    df = pd.read_csv(caminho_csv)
    return df['Ticker'].dropna().str.strip().tolist()

def salvar_json_por_ticker(dados, ticker):
    os.makedirs("data/tickers", exist_ok=True)
    caminho = f"data/tickers/{ticker}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def coletar_todos():
    tickers = carregar_tickers()
    total = len(tickers)

    with sync_playwright() as pw:
        for i, ticker in enumerate(tickers, 1):
            caminho_json = f"data/tickers/{ticker}.json"
            if os.path.exists(caminho_json):
                print(f"[{i}/{total}] {ticker} já coletado. Pulando.")
                continue
            try:
                print(f"[{i}/{total}] Coletando dados de {ticker}...")            
                # Simula navegador real com user-agent e headless desativado
               
                dados = extrair_dados_ticker(ticker, pw)
                salvar_json_por_ticker(dados, ticker)
          
                 # Delay aleatório para evitar bloqueio
                espera = random.uniform(3, 7)
                print(f"Aguardando {espera:.1f} segundos...\n")
                time.sleep(espera)

            except Exception as e:
                print(f"[ERRO] Falha ao processar {ticker}: {e}")

if __name__ == "__main__":
    coletar_todos()

