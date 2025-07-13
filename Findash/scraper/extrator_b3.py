from playwright.sync_api import TimeoutError
import time
import re

def extrair_dados_ticker(dados, pw):
    ticker = dados.get("ticker")
    if not ticker:
        raise ValueError("O campo 'ticker' é obrigatório.")

    navegador = pw.chromium.launch(headless=False)
    pagina = navegador.new_page()
    coleta_incompleta = False

    try:
        pagina.goto("https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/empresas-listadas.htm", timeout=60000)
        pagina.wait_for_selector("#bvmf_iframe", timeout=15000)
        iframe = pagina.frame_locator("#bvmf_iframe")

        iframe.get_by_role("textbox", name="Digite o nome da Empresa").fill(ticker)
        iframe.get_by_role("button", name="Buscar", exact=True).click()

        resultado = iframe.get_by_text(re.compile(ticker[:-1]), exact=False).first
        resultado.wait_for(timeout=10000)
        resultado.click()

        def extrair_secao(nome_secao):
            try:
                iframe.get_by_role("link", name=re.compile(nome_secao)).click()
                time.sleep(2)
                painel = iframe.get_by_role("tabpanel", name=re.compile(nome_secao))
                painel.wait_for(timeout=10000)
                return painel.text_content().strip()
            except:
                return None

        if dados.get("dados_economico_financeiros") is None:
            dados["dados_economico_financeiros"] = extrair_secao("Dados Econômico-Financeiros")
            if dados["dados_economico_financeiros"] is None:
                coleta_incompleta = True

        if dados.get("posicao_acionaria") is None:
            dados["posicao_acionaria"] = extrair_secao("Posição Acionária")
            if dados["posicao_acionaria"] is None:
                coleta_incompleta = True

        if dados.get("acoes_em_circulacao_no_mercado") is None:
            dados["acoes_em_circulacao_no_mercado"] = extrair_secao("Ações em Circulação no Mercado")
            if dados["acoes_em_circulacao_no_mercado"] is None:
                coleta_incompleta = True

        if dados.get("composicao_capital_social") is None:
            dados["composicao_capital_social"] = extrair_secao("Composição do Capital Social")
            if dados["composicao_capital_social"] is None:
                coleta_incompleta = True

        navegador.close()

    except Exception as e:
        dados["erro"] = str(e)
        coleta_incompleta = True
        try: navegador.close()
        except: pass

    if coleta_incompleta:
        dados["coleta_incompleta"] = True

    return dados
