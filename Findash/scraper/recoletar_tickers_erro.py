import json
from coletar_todos_tickers import salvar_json_por_ticker
from extrair_dados import extrair_dados_ticker
from playwright.sync_api import sync_playwright
import time
import random
import os

def carregar_tickers_erro(caminho="Findash/scraper/tickers_erro.json"):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)
    
def recoletar_tickers():
    tickers = carregar_tickers_erro()
    total = len(tickers)

    with sync_playwright() as pw:
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{total}] Recoletando {ticker}...")
            try:
                dados = extrair_dados_ticker(ticker, pw)
                salvar_json_por_ticker(dados, ticker)
                espera = random.uniform(3, 7)
                print(f"Aguardando {espera:.1f} segundos...\n")
                time.sleep(espera)
            except Exception as e:
                print(f"[ERRO] Falha ao recoletar {ticker}: {e}")

if __name__ == "__main__":
    recoletar_tickers()