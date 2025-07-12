import re
import time
from playwright.sync_api import TimeoutError

def montar_site_pelo_email(email):
    if not email or "@" not in email:
        return None

    dominio = email.split('@')[-1].strip().lower()
    dominios_genericos = ['gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com']

    # Ignora domínios genéricos
    if any(dominio.endswith(g) for g in dominios_genericos):
        return None

    # Verifica se é um domínio válido
    if re.match(r'^[a-zA-Z0-9.-]+\.[a-z]{2,}$', dominio):
        return f"https://{dominio}"

    return None

def coletar_site_pelo_cnpj(cnpj, pw):
    """
    Acessa o site https://cnpj.io/<CNPJ> e tenta extrair o e-mail e montar o site a partir do domínio.
    Retorna um dicionário com email e site.
    """
    url = f"https://cnpj.io/"
    site_final = None
    email_extraido = None

    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()

    try:
        page.goto(url, timeout=30000)

        # Espera o input aparecer e digita o CNPJ
        input_cnpj = page.get_by_role("textbox", name="CNPJ")
        input_cnpj.fill(cnpj)

        # Clica no botão Buscar
        botao_buscar = page.get_by_role("button", name="Buscar")
        botao_buscar.click()
        
        # Aguarda carregamento da nova página
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(3)  # Pausa extra para garantir montagem do DOM
       
        # Seletor do e-mail
        seletor_email = "h6:text('E-mail') ~ div p.form-control"
        page.wait_for_selector(seletor_email, timeout=10000)

        email_elem = page.locator(seletor_email).first
        email_extraido = email_elem.inner_text().strip()

        site_final = montar_site_pelo_email(email_extraido)


    except TimeoutError as te:
        print("[ERRO] Timeout na extração do e-mail do CNPJ.io: {te}")
    except Exception as e:
        print(f"[ERRO] Erro ao extrair e-mail do CNPJ.io: {e}")
    finally:
        browser.close()

    return {
        "email": email_extraido,
        "site": site_final
    }
