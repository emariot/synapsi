import os
import json

def consolidar_jsons_em_dicionario(pasta="data/tickers", saida="data/todos_tickers_dict.json"):
    consolidado = {}
    for arquivo in os.listdir(pasta):
        if arquivo.endswith(".json"):
            caminho = os.path.join(pasta, arquivo)
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                ticker = dados.get("ticker")
                if ticker:
                    consolidado[ticker] = dados
    with open(saida, "w", encoding="utf-8") as fout:
        json.dump(consolidado, fout, ensure_ascii=False, indent=2)
    print(f"[✓] Consolidado salvo em: {saida} com {len(consolidado)} tickers.")

if __name__ == "__main__":
    consolidar_jsons_em_dicionario()
