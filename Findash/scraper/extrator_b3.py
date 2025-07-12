from playwright.sync_api import TimeoutError
import time
import re


def extrair_dados_ticker(ticker, pw):
    navegador = pw.chromium.launch(headless=False)
    pagina = navegador.new_page()
    dados = {"ticker": ticker}
    coleta_incompleta = False

    try:
        pagina.goto("https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/empresas-listadas.htm", timeout=60000)
        pagina.wait_for_selector("#bvmf_iframe", timeout=15000)
        iframe = pagina.frame_locator("#bvmf_iframe")

        # Preencher busca
        iframe.get_by_role("textbox", name="Digite o nome da Empresa").fill(ticker)
        iframe.get_by_role("button", name="Buscar", exact=True).click()

        resultado = iframe.get_by_text(re.compile(ticker[:-1]), exact=False).first
        resultado.wait_for(timeout=10000)
        resultado.click()

        # Nome da empresa
        try:
            iframe.get_by_role("heading", name=re.compile(r".*(S[./]?A\.?|CIA|COMPANHIA).*", re.IGNORECASE)).first.wait_for(timeout=10000)
            dados["nome"] = iframe.get_by_role("heading", name=re.compile(r".*(S[./]?A\.?|CIA|COMPANHIA).*", re.IGNORECASE)).first.text_content().strip()
        except:
            dados["nome"] = None
            coleta_incompleta = True

        # Data de início
        try:
            dados["inicio_negociacao"] = iframe.get_by_text(re.compile(r"\d{2}/\d{2}/\d{4}")).first.text_content().strip()
        except:
            dados["inicio_negociacao"] = None
            coleta_incompleta = True

        # CNPJ
        try:
            dados["cnpj"] = iframe.get_by_text(re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")).first.text_content().strip()
        except:
            dados["cnpj"] = None
            coleta_incompleta = True

        # Sobre (atividade principal)
        try:
            dados["sobre"] = iframe.get_by_text("Atividade Principal").evaluate("""
                el => {
                    const next = el.parentElement?.nextElementSibling;
                    return next?.innerText || '';
                }
            """).strip()
        except:
            dados["sobre"] = None
            coleta_incompleta = True

        # Setor
        try:
            classificacao = iframe.get_by_text(re.compile(r".+ / .+ / .+")).first.text_content().strip()
            partes = [p.strip() for p in classificacao.split("/")]
            while len(partes) < 3:
                partes.append("N/D")
            if partes[1] == partes[0]: partes[1] += " (subsetor)"
            if partes[2] == partes[1] or partes[2] == partes[0]: partes[2] += " (segmento)"
            dados["setor_economico"], dados["subsetor"], dados["segmento"] = partes
        except:
            dados["setor_economico"] = dados["subsetor"] = dados["segmento"] = None
            coleta_incompleta = True

        # Site oficial - captura flexível
        # Espera presença de qualquer link http
        try:
            # Localiza o <a> cujo título vem após <strong>Site</strong>
            link = iframe.locator("xpath=//p[strong[normalize-space(text())='Site']]/following-sibling::p//a[contains(@href, 'http')]").first
            link.wait_for(timeout=5000)
            href = link.get_attribute("href")

            # Verifica se o href parece válido
            if href and any(kw in href for kw in ['http', 'www', '.com', '.com.br']):
                dados["site"] = href.strip()
            else:
                dados["site"] = None

        except Exception as e:
            dados["site"] = None
            coleta_incompleta = True
            dados["erro_site"] = f"Falha ao extrair site: {str(e)}"

        # Abas detalhadas
        def extrair_secao(nome_secao):
            try:
                iframe.get_by_role("link", name=re.compile(nome_secao)).click()
                time.sleep(2)
                painel = iframe.get_by_role("tabpanel", name=re.compile(nome_secao))
                painel.wait_for(timeout=10000)
                return painel.text_content().strip()
            except:
                return None

        dados["dados_economico_financeiros"] = extrair_secao("Dados Econômico-Financeiros")
        dados["posicao_acionaria"] = extrair_secao("Posição Acionária")
        dados["acoes_em_circulacao_no_mercado"] = extrair_secao("Ações em Circulação no Mercado")
        dados["composicao_capital_social"] = extrair_secao("Composição do Capital Social")

        navegador.close()

    except Exception as e:
        dados["erro"] = str(e)
        coleta_incompleta = True
        try: navegador.close()
        except: pass

    if coleta_incompleta:
        dados["coleta_incompleta"] = True

    return dados
