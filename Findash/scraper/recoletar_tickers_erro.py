import json
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright
from extrator_b3 import extrair_dados_ticker
from extrator_site_via_cnpj import coletar_site_pelo_cnpj
from coletar_todos_tickers import salvar_json_por_ticker

CAMINHO_TICKERS_ERRO = "Findash/scraper/tickers_erro.json"
CAMINHO_TICKERS_JSON = "Findash/data/tickers/unicos"  # onde estão os arquivos JSON salvos

def normalizar_json_final(dados: dict) -> dict:
    """
    Verifica se o dicionário possui todos os campos obrigatórios e remove 'coleta_incompleta' e 'erro_site'
    se todos os dados essenciais estiverem preenchidos, incluindo o campo 'site'.
    """
    campos_obrigatorios = [
        "ticker", "nome", "inicio_negociacao", "cnpj", "sobre",
        "setor_economico", "subsetor", "segmento", "site",
        "dados_economico_financeiros", "posicao_acionaria",
        "acoes_em_circulacao_no_mercado", "composicao_capital_social"
    ]

    completos = all(dados.get(c) not in (None, "", []) for c in campos_obrigatorios)

    if completos:
        dados.pop("coleta_incompleta", None)
        dados.pop("erro_site", None)

    return dados

def carregar_tickers_erro():
    with open(CAMINHO_TICKERS_ERRO, "r", encoding="utf-8") as f:
        return json.load(f)

def carregar_json_existente(ticker):
    caminho = Path(CAMINHO_TICKERS_JSON) / f"{ticker}.json"
    if caminho.exists():
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERRO] Falha ao ler JSON existente de {ticker}: {e}")
            return None
    return None

def recoletar_tickers():
    tickers = carregar_tickers_erro()
    total = len(tickers)

    with sync_playwright() as pw:
        for i, ticker in enumerate(tickers, 1):
            print(f"[{i}/{total}] Recoletando {ticker}...")

            dados_anteriores = carregar_json_existente(ticker)
            print(f"→ Dados anteriores para {ticker} encontrado!")

            # Testa se tem site nulo e CNPJ válido
            if (
                dados_anteriores and
                dados_anteriores.get("site") is None and
                dados_anteriores.get("cnpj")
            ):
                print("→ Informção de site ausente. Buscando no cnpj.io...")
                try:
                    resultado = coletar_site_pelo_cnpj(dados_anteriores["cnpj"], pw)
                    if resultado.get("site"):
                        dados_anteriores["site"] = resultado["site"]
                        dados_anteriores = normalizar_json_final(dados_anteriores)
                        salvar_json_por_ticker(dados_anteriores, ticker)
                        print("✓ Site preenchido via CNPJ.io e dados normalizados.")
                    else:
                        print("× CNPJ.io não retornou site. ")
                        raise Exception("CNPJ.io falhou")
                except Exception as e:
                    print(f"[ERRO fallback] Falha ao buscar no CNPJ.io: {e}")
                    print("→ Coleta pelo CNPJ.io falhou, mantendo dados para revisão manual. Não tentará nova coleta na B3.")

            else:
                print("→ Coleta completa pela B3")
                try:
                    dados = extrair_dados_ticker(dados_anteriores, pw)
                    salvar_json_por_ticker(dados, ticker)
                except Exception as e:
                    print(f"[ERRO] Falha ao recoletar via B3 {ticker}: {e}")

            espera = random.uniform(3, 7)
            print(f"Aguardando {espera:.1f} segundos...\n")
            time.sleep(espera)

if __name__ == "__main__":
    recoletar_tickers()
