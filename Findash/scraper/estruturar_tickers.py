import re
import json

def limpar_texto(texto):
    """
    Insere espaços entre números grudados:
    - Ex: '1.603.8521.600.313' -> '1.603.852 1.600.313'
    """
    # Regex que identifica quando um número termina e outro começa imediatamente
    # Procura dígito seguido imediatamente por outro dígito e um ponto decimal, separa por espaço
    # Também procura parênteses e separa para evitar mistura
    texto = re.sub(r'(\d)(?=(\d{1,3}\.))', r'\1 ', texto)
    texto = re.sub(r'(\))(?=\d)', r') ', texto)
    texto = re.sub(r'(\d)(?=\()', r'\1 ', texto)
    return texto

def converte_num_brasileiro(valor):
    """
    Converte número formatado no padrão brasileiro para int,
    tratando negativo entre parênteses.
    """
    valor = valor.strip()
    if not valor:
        return None
    negativo = False
    if valor.startswith('(') and valor.endswith(')'):
        negativo = True
        valor = valor[1:-1]

    # Remove pontos e troca vírgula por ponto (para float)
    valor = valor.replace('.', '').replace(',', '.')
    try:
        n = float(valor)
        n_int = int(round(n))
        return -n_int if negativo else n_int
    except Exception:
        return None

def extrair_dados(texto, campos, datas_esperadas):
    """
    Extrai para cada campo seus valores numéricos correspondentes.
    Retorna dict {campo: {data1: val1, data2: val2}}
    """
    dados = {}
    for campo in campos:
        # Escapa caracteres especiais no campo para regex
        campo_escapado = re.escape(campo)
        # Busca a linha com campo seguido de dois números (podem ter parênteses)
        regex = re.compile(rf'{campo_escapado}\s*([\(\)\d\.,\-]+)\s*([\(\)\d\.,\-]+)')
        match = regex.search(texto)
        if match:
            v1 = converte_num_brasileiro(match.group(1))
            v2 = converte_num_brasileiro(match.group(2))
            dados[campo.lower().replace(' ', '_').replace('á','a').replace('à','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ç','c').replace('(','').replace(')','')] = {
                datas_esperadas[0]: v1,
                datas_esperadas[1]: v2
            }
    return dados

def parse_dados_economicos(texto_bruto):
    texto = limpar_texto(texto_bruto)

    # Datas do balanço patrimonial - aparecem juntas no texto
    datas_bp = re.findall(r'\d{2}/\d{2}/\d{4}', texto)
    datas_bp = list(dict.fromkeys(datas_bp))  # Remove duplicados mantendo ordem
    if len(datas_bp) < 2:
        raise ValueError("Não encontrou 2 datas no balanço patrimonial")

    campos_bp = [
        "Ativo Imobilizado, Investimentos e Intangível",
        "Ativo Total",
        "Patrimônio Líquido",
        "Patrimônio Líquido Atribuído à Controladora"
    ]

    campos_dr = [
        "Receita de Venda",
        "Resultado Bruto",
        "Resultado de Equivalência Patrimonial",
        "Resultado Financeiro",
        "Resultado Líquido das Operações Continuadas",
        "Lucro (Prejuízo) do Período",
        "Lucro (Prejuízo) do Período Atribuído à Controladora"
    ]

    # Datas da Demonstração do Resultado e Fluxo de Caixa (formato 01/01/2025 a 31/03/2025)
    datas_dr = re.findall(r'\d{2}/\d{2}/\d{4} a \d{2}/\d{2}/\d{4}', texto)
    if len(datas_dr) < 2:
        raise ValueError("Não encontrou 2 datas no demonstrativo de resultado")

    campos_fc = [
        "Atividades Operacionais",
        "Atividades de Investimento",
        "Atividades de Financiamento",
        "Variação Cambial sobre Caixa e Equivalentes",
        "Aumento (Redução) de Caixa e Equivalentes"
    ]

    dados = {
        "balanco_patrimonial": extrair_dados(texto, campos_bp, datas_bp[:2]),
        "demonstracao_resultado": extrair_dados(texto, campos_dr, datas_dr[:2]),
        "fluxo_caixa": extrair_dados(texto, campos_fc, datas_dr[:2]),
    }

    return dados


if __name__ == "__main__":
    texto_teste = """
    Ver dados no formato Consolidado  Não consolidado Balanço Patrimonial  - Consolidado31/03/202531/12/2024Ativo Imobilizado, Investimentos e Intangível1.603.8521.600.313Ativo Total2.859.0062.889.222Patrimônio Líquido1.114.9151.136.817Patrimônio Líquido Atribuído à Controladora1.074.9751.094.793Demonstração do Resultado - Consolidado01/01/2025 a 31/03/202501/01/2024 a 31/03/2024Receita de Venda307.063280.709Resultado Bruto72.79180.617Resultado de Equivalência Patrimonial00Resultado Financeiro(39.572)(71.143)Resultado Líquido das Operações Continuadas(21.208)(76.845)Lucro (Prejuízo) do Período(21.208)(76.845)Lucro (Prejuízo) do Período Atribuído à Controladora(19.828)(78.744)Demonstração do Fluxo de Caixa - Consolidado01/01/2025 a 31/03/202501/01/2024 a 31/03/2024Atividades Operacionais73.9045.689Atividades de Investimento36.349(20.411)Atividades de Financiamento(102.955)(106.085)Variação Cambial sobre Caixa e Equivalentes00Aumento (Redução) de Caixa e Equivalentes7.298(120.807)
    """
    resultado = parse_dados_economicos(texto_teste)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
