import os
import json

def consolidar_todos_jsons(pasta="data/tickers", saida="data/dados_brutos_todos_tickers.json"):
    todos = []
    for arquivo in sorted(os.listdir(pasta)):
        if arquivo.endswith(".json"):
            caminho = os.path.join(pasta, arquivo)
            with open(caminho, "r", encoding="utf-8") as f:
                try:
                    dados = json.load(f)
                    todos.append(dados)
                except json.JSONDecodeError:
                    print(f"[!] Erro ao carregar {arquivo}, ignorado.")
    with open(saida, "w", encoding="utf-8") as fout:
        json.dump(todos, fout, ensure_ascii=False, indent=2)
    print(f"Arquivo final salvo em {saida} com {len(todos)} entradas.")

if __name__ == "__main__":
    consolidar_todos_jsons()
