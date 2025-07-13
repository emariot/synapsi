import os
import json
from pathlib import Path

PASTA = Path("data/tickers")

def arquivo_com_erro(dados):
    erros = []

    if dados.get("site_error") is True:
        erros.append("site_error")

    for chave, valor in dados.items():
        if valor is None:
            erros.append(f"null_field: {chave}")

    return erros

def listar_arquivos_com_erros():
    for arquivo in PASTA.glob("*.json"):
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)

            erros = arquivo_com_erro(dados)
            if erros:
                print(f"{arquivo.name} → {', '.join(erros)}")

        except Exception as e:
            print(f"[FALHA] Erro ao ler {arquivo.name}: {e}")

if __name__ == "__main__":
    print("--- Arquivos com site_error ou campos nulos ---\n")
    listar_arquivos_com_erros()
