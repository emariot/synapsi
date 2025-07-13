import os
import json
import re
from pathlib import Path

PASTA_ORIGINAL = Path("data/tickers")
PASTA_DESTINO = Path("data/tickers_estruturados")
RELATORIO_ERROS = "relatorio_erros_estrutura.json"

os.makedirs(PASTA_DESTINO, exist_ok=True)
erros = {}

def parse_numero(s):
    if not s:
        return None
    s = s.strip()
    if s in ("-", "", None):
        return None
    s = s.replace('.', '').replace(',', '.')
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    try:
        return float(s)
    except:
        return None

def estruturar_dados_eco(texto):
    if not texto:
        return None
    
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    secoes_chaves = {
        "balanco_patrimonial": "Balanço Patrimonial",
        "demonstracao_resultado": "Demonstração do Resultado",
        "demonstracao_fluxo_caixa": "Demonstração do Fluxo de Caixa"
    }

    secoes = {}
    secao_atual = None
    datas = []
    valores = {}

    for linha in linhas:
        # Detecta o início da seção e datas
        for chave, titulo in secoes_chaves.items():
            if titulo in linha:
                # Salva seção anterior se existir
                if secao_atual:
                    secoes[secao_atual] = {"datas": datas, "valores": valores}
                secao_atual = chave
                # Extrai as datas da linha
                datas = re.findall(r'\d{2}/\d{2}/\d{4}', linha)
                valores = {}
                break
        else:
            # Linha dentro da seção: tenta extrair nome + valores
            if secao_atual:
                # Dividir por 2 ou mais espaços consecutivos (colunas)
                partes = re.split(r'\s{2,}', linha)
                if len(partes) >= 2:
                    nome = partes[0]
                    numeros = [parse_numero(x) for x in partes[1:]]
                    valores[nome] = numeros

    # Salva a última seção processada
    if secao_atual:
        secoes[secao_atual] = {"datas": datas, "valores": valores}

    return secoes

def estruturar_posicao_acionaria(texto):
    if not texto:
        return None
    # Exemplo: Nome %ON %PN %Total separados por tabulação ou múltiplos espaços
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    resultado = []
    for linha in linhas:
        # Tentativa simples: dividir por tab ou 2+ espaços
        campos = re.split(r'\t+|\s{2,}', linha)
        if len(campos) >= 4:
            nome = campos[0]
            try:
                on = float(campos[1].replace(',', '.'))
            except:
                on = None
            try:
                pn = float(campos[2].replace(',', '.'))
            except:
                pn = None
            try:
                total = float(campos[3].replace(',', '.'))
            except:
                total = None
            resultado.append({"nome": nome, "%ON": on, "%PN": pn, "%Total": total})
    return resultado

def estruturar_acoes_em_circulacao(texto):
    if not texto:
        return None
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    resultado = []
    for linha in linhas:
        # Tenta separar em três colunas: tipo, quantidade, percentual
        campos = re.split(r'\t+|\s{2,}', linha)
        if len(campos) >= 3:
            tipo = campos[0]
            qtd = parse_numero(campos[1])
            perc = campos[2].replace(',', '.') if campos[2] != '-' else None
            try:
                perc = float(perc) if perc else None
            except:
                perc = None
            resultado.append({"tipo": tipo, "quantidade": qtd, "percentual": perc})
    return resultado

def estruturar_capital_social(texto):
    if not texto:
        return None
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    resultado = {}
    for linha in linhas:
        # Espera formato "Ordinárias\t123456", etc
        campos = re.split(r'\t+|\s{2,}', linha)
        if len(campos) >= 2:
            chave = campos[0].lower()
            valor = parse_numero(campos[1])
            if chave and valor is not None:
                # padronizar chaves
                if 'ordinaria' in chave:
                    resultado['ordinarias'] = valor
                elif 'preferencial' in chave:
                    resultado['preferenciais'] = valor
                elif 'total' in chave:
                    resultado['total'] = valor
    return resultado if resultado else None

def processar_arquivo(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)

        # Substitui os campos originais pelos estruturados
        if "dados_economico_financeiros" in dados:
            dados["dados_economico_financeiros"] = estruturar_dados_eco(dados["dados_economico_financeiros"])

        if "posicao_acionaria" in dados:
            dados["posicao_acionaria"] = estruturar_posicao_acionaria(dados["posicao_acionaria"])

        if "acoes_em_circulacao_no_mercado" in dados:
            dados["acoes_em_circulacao_no_mercado"] = estruturar_acoes_em_circulacao(dados["acoes_em_circulacao_no_mercado"])

        if "composicao_capital_social" in dados:
            dados["composicao_capital_social"] = estruturar_capital_social(dados["composicao_capital_social"])

        destino = PASTA_DESTINO / caminho.name
        with open(destino, "w", encoding="utf-8") as f_out:
            json.dump(dados, f_out, ensure_ascii=False, indent=2)

    except Exception as e:
        erros[caminho.name] = str(e)

def main():
    arquivos = list(PASTA_ORIGINAL.glob("*.json"))
    total = len(arquivos)
    print(f"Processando {total} arquivos...")

    for i, caminho in enumerate(arquivos, 1):
        print(f"[{i}/{total}] {caminho.name}")
        processar_arquivo(caminho)

    with open(RELATORIO_ERROS, "w", encoding="utf-8") as f:
        json.dump(erros, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Concluído. {len(erros)} arquivos com erro.")
    print(f"→ Relatório salvo em: {RELATORIO_ERROS}")
    print(f"→ Arquivos salvos em: {PASTA_DESTINO}")

if __name__ == "__main__":
    main()
