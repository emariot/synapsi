import os
import json

def verificar_coletas(pasta="data/tickers"):
    tickers_ok = []
    tickers_erro = []

    for arquivo in os.listdir(pasta):
        if not arquivo.endswith(".json"):
            continue
        caminho = os.path.join(pasta, arquivo)

        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)

            ticker = dados.get("ticker", arquivo.replace(".json", ""))
            # Verifica se existe 'erro' ou 'coleta_incompleta' ou qualquer campo com valor None
            if (
                "erro" in dados
                or dados.get("coleta_incompleta")
                or any(v is None for v in dados.values())
            ):
                tickers_erro.append(ticker)
            else:
                tickers_ok.append(ticker)

        except Exception as e:
            print(f"[!] Erro ao ler {arquivo}: {e}")
            tickers_erro.append(arquivo.replace(".json", ""))

    print(f"\n✓ {len(tickers_ok)} tickers com dados completos.")
    print(f"✗ {len(tickers_erro)} tickers com erro ou incompletos.")

    # Salva os resultados
    with open("tickers_ok.json", "w", encoding="utf-8") as f:
        json.dump(tickers_ok, f, indent=2)

    with open("tickers_erro.json", "w", encoding="utf-8") as f:
        json.dump(tickers_erro, f, indent=2)

    return tickers_ok, tickers_erro

if __name__ == "__main__":
    verificar_coletas()
