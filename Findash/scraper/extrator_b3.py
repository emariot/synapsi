from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup
import time
import re
import json
import os

def salvar_dados_extraidos(dados_extraidos, pasta="data/tickers"):
    ticker = dados_extraidos.get("ticker")
    if not ticker:
        raise ValueError("Ticker ausente nos dados extraídos.")

    caminho_arquivo = os.path.join(pasta, f"{ticker}.json")

    if not os.path.exists(caminho_arquivo):
        raise FileNotFoundError(f"Arquivo {caminho_arquivo} não encontrado.")

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        dados_existentes = json.load(f)

    # Atualiza os campos de dados coletados
    campos_para_atualizar = [
        "dados_economico_financeiros",
        "posicao_acionaria",
        "acoes_em_circulacao_no_mercado",
        "composicao_capital_social"
    ]

    for campo in campos_para_atualizar:
        if campo in dados_extraidos and dados_extraidos[campo]:
            dados_existentes[campo] = dados_extraidos[campo]

    # Se houve falha, adiciona campos de erro
    if dados_extraidos.get("coleta_incompleta") or dados_extraidos.get("erro"):
        if "coleta_incompleta" in dados_extraidos:
            dados_existentes["coleta_incompleta"] = True
        if "erro" in dados_extraidos:
            dados_existentes["erro"] = dados_extraidos["erro"]
    else:
        # Se tudo deu certo, remove campos de erro, se existirem
        dados_existentes.pop("coleta_incompleta", None)
        dados_existentes.pop("erro", None)

    # Salva o arquivo atualizado
    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados_existentes, f, ensure_ascii=False, indent=2)

    print(f"[✓] Arquivo atualizado com sucesso: {caminho_arquivo}")



def extrair_tabelas_dados_financeiros(html):
    soup = BeautifulSoup(html, "lxml")
    resultado = {
        "balanco_patrimonial": {},
        "demonstracao_resultado": {},
        "fluxo_caixa": {}
    }

    tabelas = soup.select("table.table")
    nomes_tabelas = list(resultado.keys())

    for i, tabela in enumerate(tabelas):
        if i >= len(nomes_tabelas):
            break  # ignora qualquer tabela extra
        tipo = nomes_tabelas[i]

        headers = tabela.select("thead tr th")
        if len(headers) < 3:
            continue  # ignora se cabeçalhos incompletos

        datas = [
            headers[1].get_text(strip=True).replace(" ", "_"),
            headers[2].get_text(strip=True).replace(" ", "_")
        ]

        linhas = tabela.select("tbody tr")
        for linha in linhas:
            campos = linha.select("td")
            if len(campos) < 3:
                continue

            chave = (
                campos[0].get_text(strip=True)
                .lower()
                .replace(" ", "_")
                .replace("(", "").replace(")", "")
                .replace(".", "").replace(",", "")
                .replace("ã", "a").replace("ç", "c")
                .replace("é", "e").replace("ê", "e")
                .replace("á", "a").replace("í", "i")
                .replace("ú", "u").replace("ó", "o")
            )

            def converter(valor):
                valor = valor.replace(".", "").replace(",", "")
                valor = valor.replace("(", "-").replace(")", "")
                return int(valor) if valor.isdigit() or valor.lstrip("-").isdigit() else None

            resultado[tipo][chave] = {
                datas[0]: converter(campos[1].get_text(strip=True)),
                datas[1]: converter(campos[2].get_text(strip=True))
            }

    return resultado

def parse_posicao_acionaria(html):
    soup = BeautifulSoup(html, "lxml")
    resultado = []
    linhas = soup.select("tbody tr")
    for linha in linhas:
        colunas = linha.select("td")
        if len(colunas) >= 4:
            resultado.append({
                "nome": colunas[0].get_text(strip=True),
                "ON": float(colunas[1].get_text(strip=True).replace(",", ".")),
                "PN": float(colunas[2].get_text(strip=True).replace(",", ".")),
                "Total": float(colunas[3].get_text(strip=True).replace(",", "."))
            })
    return resultado

def parse_acoes_em_circulacao(html):
    soup = BeautifulSoup(html, "lxml")
    resultado = {
        "tipos_investidores": []
    }

    data_th = soup.select_one("thead tr th[colspan]")
    if data_th:
        resultado["data"] = data_th.get_text(strip=True)

    linhas = soup.select("tbody tr")
    for linha in linhas:
        colunas = linha.select("td")
        if len(colunas) >= 3:
            tipo = colunas[0].get_text(strip=True)
            quantidade = colunas[1].get_text(strip=True).replace(".", "")
            percentual = colunas[2].get_text(strip=True).replace(",", ".")
            if "Quantidade de Ações Ordinárias" in tipo:
                resultado["quantidade_acoes_ordinarias"] = int(quantidade)
                resultado["percentual_ordinarias"] = float(percentual)
            elif "Total de Ações" in tipo:
                resultado["total_acoes"] = int(quantidade)
                resultado["percentual_total"] = float(percentual)
            else:
                resultado["tipos_investidores"].append({
                    "tipo": tipo,
                    "quantidade": int(quantidade) if quantidade.isdigit() else None,
                    "percentual": float(percentual) if percentual.replace(".", "").isdigit() else None
                })
    return resultado

def parse_composicao_capital(html):
    soup = BeautifulSoup(html, "lxml")
    resultado = {}
    data_th = soup.select_one("thead tr th[colspan]")
    if data_th:
        resultado["data"] = data_th.get_text(strip=True)

    linhas = soup.select("tbody tr")
    for linha in linhas:
        colunas = linha.select("td")
        if len(colunas) == 2:
            chave = colunas[0].get_text(strip=True).lower()
            valor = int(colunas[1].get_text(strip=True).replace(".", ""))
            if "ordinarias" in chave:
                resultado["ordinarias"] = valor
            elif "preferenciais" in chave:
                resultado["preferenciais"] = valor
            elif "total" in chave:
                resultado["total"] = valor
    return resultado

def extrair_dados_ticker(dados, pw):
    ticker = dados.get("ticker")
    if not ticker:
        raise ValueError("O campo 'ticker' é obrigatório.")
    
    for campo in [
        "dados_economico_financeiros",
        "posicao_acionaria",
        "acoes_em_circulacao_no_mercado",
        "composicao_capital_social"
    ]:
        if isinstance(dados.get(campo), str):
            dados[campo] = None

    navegador = pw.chromium.launch(headless=False, slow_mo=200)
    pagina = navegador.new_page()
    coleta_incompleta = False

    try:
        print(f"Acessando página da B3 para {ticker}...")
        pagina.goto("https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/empresas-listadas.htm", timeout=60000)
        pagina.wait_for_selector("#bvmf_iframe", timeout=15000)
        iframe = pagina.frame_locator("#bvmf_iframe")

        print("Preenchendo campo de busca...")
        iframe.get_by_role("textbox", name="Digite o nome da Empresa").fill(ticker)
        iframe.get_by_role("button", name="Buscar", exact=True).click()

        print("Aguardando resultados e clicando na empresa...")
        resultado = iframe.get_by_text(re.compile(ticker[:-1], re.IGNORECASE)).first
        resultado.wait_for(timeout=10000)
        resultado.click()

        print("Aguardando navegação para detalhes da empresa...")
        time.sleep(3)  # Dá tempo para a nova página carregar

        def extrair_secao(nome_secao):
            try:
                print(f"Abrindo seção: {nome_secao}")
                iframe.get_by_role("link", name=re.compile(nome_secao)).click()
                time.sleep(2)
                painel = iframe.get_by_role("tabpanel", name=re.compile(nome_secao))
                painel.wait_for(timeout=10000)
                return painel.inner_html()
            except Exception as e:
                print(f"[ERRO] Não foi possível extrair {nome_secao}: {e}")
                return None

        if not dados.get("dados_economico_financeiros"):
            html_financeiros = extrair_secao("Dados Econômico-Financeiros")
            if html_financeiros:
                try:
                    dados["dados_economico_financeiros"] = extrair_tabelas_dados_financeiros(html_financeiros)
                except Exception as e:
                    print(f"[ERRO] Parse dos dados econômicos falhou: {e}")
                    dados["dados_economico_financeiros"] = None
                    coleta_incompleta = True
            else:
                dados["dados_economico_financeiros"] = None
                coleta_incompleta = True

        if not dados.get("posicao_acionaria"):
            html_acionaria = extrair_secao("Posição Acionária")
            if html_acionaria:
                dados["posicao_acionaria"] = parse_posicao_acionaria(html_acionaria)
            else:
                dados["posicao_acionaria"] = None
                coleta_incompleta = True

        if not dados.get("acoes_em_circulacao_no_mercado"):
            html_circulacao = extrair_secao("Ações em Circulação no Mercado")
            if html_circulacao:
                dados["acoes_em_circulacao_no_mercado"] = parse_acoes_em_circulacao(html_circulacao)
            else:
                dados["acoes_em_circulacao_no_mercado"] = None
                coleta_incompleta = True


        if not dados.get("composicao_capital_social"):
            html_capital = extrair_secao("Composição do Capital Social")
            if html_capital:
                dados["composicao_capital_social"] = parse_composicao_capital(html_capital)
            else:
                dados["composicao_capital_social"] = None
                coleta_incompleta = True

    except Exception as e:
        print(f"[ERRO] Falha geral para o ticker {ticker}: {e}")
        dados["erro"] = str(e)
        coleta_incompleta = True

    finally:
        navegador.close()

    if coleta_incompleta:
        dados["coleta_incompleta"] = True

    return dados

# Exemplo de uso
if __name__ == "__main__":
    pasta_tickers = "data/tickers"
    arquivos = [f for f in os.listdir(pasta_tickers) if f.endswith(".json")]
    with sync_playwright() as pw:
        for arquivo in arquivos:
            caminho = os.path.join(pasta_tickers, arquivo)
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)

                ticker = dados.get("ticker")
                if not ticker:
                    print(f"[!] Arquivo {arquivo} sem campo 'ticker'. Ignorando.")
                    continue

                print(f"\n[+] Processando ticker: {ticker}")
                resultado = extrair_dados_ticker(dados, pw)
                salvar_dados_extraidos(resultado, pasta=pasta_tickers)

            except Exception as e:
                print(f"[ERRO] Falha ao processar arquivo {arquivo}: {e}")
