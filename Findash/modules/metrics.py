import yfinance as yf
import pandas as pd
import time
import functools
from datetime import datetime

# Decorador para medir tempo de execução
def measure_time(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{func.__name__}: Tempo de execução = {execution_time:.4f}s")
        return result
    return wrapper

# Mapeamento manual inicial baseado na B3 (50 tickers populares como exemplo)
SETOR_MAP = {
    "PETR4.SA": "Petróleo, Gás e Biocombustíveis",
    "VALE3.SA": "Materiais Básicos",
    "ITUB4.SA": "Financeiro e Outros",
    "BBDC4.SA": "Financeiro e Outros",
    "ABEV3.SA": "Consumo Não Cíclico",
    "CSAN3.SA": "Petróleo, Gás e Biocombustíveis",
    "PRIO3.SA": "Petróleo, Gás e Biocombustíveis",
    "UGPA3.SA": "Petróleo, Gás e Biocombustíveis",
    "VBBR3.SA": "Petróleo, Gás e Biocombustíveis",
    "BRAP4.SA": "Materiais Básicos",
    "CSNA3.SA": "Materiais Básicos",
    "GGBR4.SA": "Materiais Básicos",
    "USIM5.SA": "Materiais Básicos",
    "BRKM5.SA": "Materiais Básicos",
    "SUZB3.SA": "Materiais Básicos",
    "EMBR3.SA": "Bens Industriais",
    "WEGE3.SA": "Bens Industriais",
    "RAIL3.SA": "Bens Industriais",
    "CCRO3.SA": "Bens Industriais",
    "ECOR3.SA": "Bens Industriais",
    "BRFS3.SA": "Consumo Não Cíclico",
    "JBSS3.SA": "Consumo Não Cíclico",
    "MRFG3.SA": "Consumo Não Cíclico",
    "BEEF3.SA": "Consumo Não Cíclico",
    "SMTO3.SA": "Consumo Não Cíclico",
    "MGLU3.SA": "Consumo Cíclico",
    "LREN3.SA": "Consumo Cíclico",
    "BHIA3.SA": "Consumo Cíclico",
    "MRVE3.SA": "Consumo Cíclico",
    "CYRE3.SA": "Consumo Cíclico",
    "RADL3.SA": "Saúde",
    "HAPV3.SA": "Saúde",
    "FLRY3.SA": "Saúde",
    "DASA3.SA": "Saúde",
    "QUAL3.SA": "Saúde",
    "TOTS3.SA": "Tecnologia e Comunicação",
    "POSI3.SA": "Tecnologia e Comunicação",
    "LWSA3.SA": "Tecnologia e Comunicação",
    "VIVT3.SA": "Tecnologia e Comunicação",
    "TIMP3.SA": "Tecnologia e Comunicação",
    "CMIG4.SA": "Utilidade Pública",
    "CPLE6.SA": "Utilidade Pública",
    "EGIE3.SA": "Utilidade Pública",
    "SBSP3.SA": "Utilidade Pública",
    "EQTL3.SA": "Utilidade Pública",
    "BBAS3.SA": "Financeiro e Outros",
    "SANB11.SA": "Financeiro e Outros",
    "B3SA3.SA": "Financeiro e Outros",
    "ITSA4.SA": "Financeiro e Outros",
    "BBSE3.SA": "Financeiro e Outros",
}

# Conversão de setores do yfinance para nossos 9 setores
YFINANCE_SECTOR_MAP = {
    "Energy": "Petróleo, Gás e Biocombustíveis",
    "Basic Materials": "Materiais Básicos",
    "Industrials": "Bens Industriais",
    "Consumer Defensive": "Consumo Não Cíclico",
    "Consumer Cyclical": "Consumo Cíclico",
    "Healthcare": "Saúde",
    "Technology": "Tecnologia e Comunicação",
    "Communication Services": "Tecnologia e Comunicação",
    "Utilities": "Utilidade Pública",
    "Financial Services": "Financeiro e Outros",
    "Real Estate": "Financeiro e Outros",
}

# Lista de setores para inicialização de dicionários
SETORES = [
    "Petróleo, Gás e Biocombustíveis",
    "Materiais Básicos",
    "Bens Industriais",
    "Consumo Não Cíclico",
    "Consumo Cíclico",
    "Saúde",
    "Tecnologia e Comunicação",
    "Utilidade Pública",
    "Financeiro e Outros",
]

@measure_time
def get_sector(ticker):
    """Obtém o setor do ticker, usando mapeamento manual ou yfinance como fallback."""
    if ticker in SETOR_MAP:
        return SETOR_MAP[ticker]
    try:
        stock = yf.Ticker(ticker)
        sector = stock.info.get("sector", "Unknown")
        return YFINANCE_SECTOR_MAP.get(sector, "Financeiro e Outros")
    except Exception as e:
        print(f"Erro ao consultar setor de {ticker}: {e}")
        return "Financeiro e Outros"

@measure_time
def obter_dados(tickers, start_date, end_date, include_ibov=True):
    """
    Obtém dados de preços ajustados e dividendos para uma lista de tickers.
    
    Args:
        tickers (list): Lista de tickers (e.g., ['PETR4.SA', 'VALE3.SA']).
        start_date (str): Data inicial (formato 'YYYY-MM-DD').
        end_date (str): Data final (formato 'YYYY-MM-DD').
        include_ibov (bool): Se True, inclui dados do IBOV (^BVSP).
    
    Returns:
        dict: Contém 'portfolio', 'ibov', 'dividends'.
    """

    result = {'portfolio': {t: {} for t in tickers}, 'ibov': {}, 'dividends': {t: {} for t in tickers}}
    valid_tickers = []

    tickers_to_download = tickers + ['^BVSP'] if include_ibov else tickers

    if tickers_to_download:
        try:
            start_time = time.time()
            data = yf.download(
                tickers_to_download, 
                start=start_date, 
                end=end_date,
                auto_adjust=False,
                actions=True,
                progress=False,
                timeout=10
            )
            print(f"yf.download took {time.time() - start_time}s")
            
            if data.empty:
                print(f"Nenhum dado retornado para {tickers_to_download}")
                return result

            available_columns = data.columns.get_level_values(0).unique()
            if 'Adj Close' not in available_columns:
                print(f"'Adj Close' não encontrado para {tickers_to_download}")
                return result
            adj_close = data['Adj Close']

            if 'Dividends' in available_columns:
                dividends_data = data['Dividends']
            else:
                print("Nenhum dado de dividendos retornado pelo yfinance")
                dividends_data = None

            valid_tickers = [t for t in tickers if t in adj_close.columns and not adj_close[t].isna().all()]
            if valid_tickers:
                adj_close_portfolio = adj_close[valid_tickers]
                print(f"Portfolio: {len(adj_close_portfolio)} linhas para {valid_tickers}")
                adj_close_portfolio.index = adj_close_portfolio.index.map(lambda x: x.strftime('%Y-%m-%d'))
                result['portfolio'].update(adj_close_portfolio.to_dict())
            else:
                print(f"Nenhum dado válido para {tickers}")

            if include_ibov and '^BVSP' in adj_close.columns:
                ibov_adj_close = adj_close['^BVSP'].dropna()
                print(f"IBOV: {len(ibov_adj_close)} linhas")
                ibov_adj_close.index = ibov_adj_close.index.map(lambda x: x.strftime('%Y-%m-%d'))
                result['ibov'] = ibov_adj_close.to_dict()
            elif include_ibov:
                print("Nenhum dado para IBOV (^BVSP)")

            if dividends_data is not None:
                for ticker in valid_tickers:
                    ticker_dividends = dividends_data[ticker].dropna()
                    if not ticker_dividends.empty:
                        ticker_dividends = ticker_dividends.loc[start_date:end_date]
                        ticker_dividends.index = ticker_dividends.index.map(lambda x: x.strftime('%Y-%m-%d'))
                        result['dividends'][ticker] = ticker_dividends.to_dict()
                    else:
                        result['dividends'][ticker] = {}
            else:
                for ticker in valid_tickers:
                    result['dividends'][ticker] = {}

        except Exception as e:
            print(f"Erro ao obter dados do yfinance: {e}")
            for ticker in tickers:
                result['portfolio'][ticker] = {}
                result['dividends'][ticker] = {}
            if include_ibov:
                result['ibov'] = {}

    return result

# Funções auxiliares para cálculos repetitivos
@measure_time
def obter_preco_inicial_e_final(prices):
    """
    Obtém o preço inicial e final de uma série de preços.
    
    Args:
        prices (dict): Dicionário de preços {data: preço}.
    
    Returns:
        tuple: (preco_inicial, preco_final), ou (None, None) se não houver dados válidos.
    """
    if not prices:
        return None, None
    datas_ordenadas = sorted(prices.keys())
    preco_inicial = prices[datas_ordenadas[0]]
    preco_final = prices[datas_ordenadas[-1]]
    return preco_inicial, preco_final

@measure_time
def calcular_percentual(valor, total):
    """
    Calcula o percentual de um valor em relação a um total.
    
    Args:
        valor (float): Valor a ser convertido em percentual.
        total (float): Total para cálculo do percentual.
    
    Returns:
        float: Percentual (0.0 se total for 0).
    """
    return (valor / total) * 100 if total > 0 else 0.0

# Funções menores para cada tipo de cálculo
@measure_time
def calcular_pesos_por_setor(tickers, quantities, portfolio, get_sector_func=get_sector):
    """
    Calcula os pesos por setor com base na quantidade e no valor financeiro.
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        portfolio (dict): Dicionário de preços {ticker: {data: preço}}.
    
    Returns:
        tuple: (setor_pesos, setor_pesos_financeiros), dicionários com os pesos por setor.
    """
    # Inicializar dicionários de pesos por setor
    setor_pesos = {setor: 0.0 for setor in SETORES}
    setor_pesos_financeiros = {setor: 0.0 for setor in SETORES}

    # Calcular soma total das quantidades
    soma_quantidades = sum(quantities)

    # Calcular valor financeiro total
    valor_total = 0.0
    for i, ticker in enumerate(tickers):
        if ticker in portfolio and portfolio[ticker]:
            precos = portfolio[ticker]
            preco_inicial, preco_final = obter_preco_inicial_e_final(precos)
            if preco_final is not None:
                quantidade = quantities[i]
                # Peso por quantidade
                peso_quantidade = calcular_percentual(quantidade, soma_quantidades)
                setor = get_sector_func(ticker)
                setor_pesos[setor] += peso_quantidade
                # Peso financeiro
                valor_financeiro = quantidade * preco_final
                valor_total += valor_financeiro
                setor_pesos_financeiros[setor] += valor_financeiro

    # Converter pesos financeiros para percentuais
    for setor in setor_pesos_financeiros:
        setor_pesos_financeiros[setor] = calcular_percentual(setor_pesos_financeiros[setor], valor_total)

    return setor_pesos, setor_pesos_financeiros

@measure_time
def calcular_retornos_individuais(tickers, portfolio):
    """
    Calcula os retornos acumulados e diários para cada ticker.
    
    Args:
        tickers (list): Lista de tickers.
        portfolio (dict): Dicionário de preços {ticker: {data: preço}}.
    
    Returns:
        tuple: (individual_returns_dict, individual_daily_returns_dict)
            - individual_returns_dict: Retornos acumulados por ticker.
            - individual_daily_returns_dict: Retornos diários por ticker.
    """
    df_portfolio = pd.DataFrame(portfolio)
    df_portfolio = df_portfolio[tickers]

    if df_portfolio.empty or df_portfolio.shape[0] == 0:
        print("Nenhum dado válido para calcular retornos individuais")
        return (
            {ticker: {} for ticker in tickers},
            {ticker: {} for ticker in tickers}
        )

    individual_returns_df = (df_portfolio / df_portfolio.iloc[0] - 1) * 100
    individual_returns_dict = {
        ticker: individual_returns_df[ticker].to_dict()
        for ticker in tickers if ticker in individual_returns_df.columns
    }

    daily_returns_df = df_portfolio.pct_change(fill_method=None) * 100
    individual_daily_returns_dict = {
        ticker: daily_returns_df[ticker].dropna().to_dict()
        for ticker in tickers if ticker in daily_returns_df.columns
    }

    return individual_returns_dict, individual_daily_returns_dict
@measure_time
def calcular_retornos_portfolio(tickers, quantities, portfolio):
    """
    Calcula os retornos acumulados e diários do portfólio.
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        portfolio (dict): Dicionário de preços {ticker: {data: preço}}.
    
    Returns:
        tuple: (portfolio_return_dict, portfolio_daily_return_dict)
            - portfolio_return_dict: Retornos acumulados do portfólio.
            - portfolio_daily_return_dict: Retornos diários do portfólio.
    """
    df_portfolio = pd.DataFrame(portfolio)
    df_portfolio = df_portfolio[tickers]

    quantities_dict = dict(zip(tickers, quantities))
    portfolio_values = df_portfolio * pd.Series(quantities_dict)
    portfolio_total = portfolio_values.sum(axis=1)

    # Retornos acumulados
    portfolio_return = (portfolio_total / portfolio_total.iloc[0] - 1) * 100
    portfolio_return_dict = portfolio_return.to_dict()

    # Retornos diários
    portfolio_daily_return = portfolio_total.pct_change() * 100
    portfolio_daily_return_dict = portfolio_daily_return.dropna().to_dict()

    return portfolio_return_dict, portfolio_daily_return_dict

@measure_time
def calcular_valores_portfolio(tickers, quantities, portfolio):
    """
    Calcula os valores do portfólio ao longo do tempo.
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        portfolio (dict): Dicionário de preços {ticker: {data: preço}}.
    
    Returns:
        dict: Dicionário com os valores do portfólio (portfolio_values.to_dict()).
    """
    df_portfolio = pd.DataFrame(portfolio)
    df_portfolio = df_portfolio[tickers]

    quantities_dict = dict(zip(tickers, quantities))
    portfolio_values = df_portfolio * pd.Series(quantities_dict)

    return portfolio_values.to_dict()

@measure_time
def calcular_retorno_ibov(ibov):
    """
    Calcula o retorno acumulado do IBOV.
    
    Args:
        ibov (dict): Dicionário de preços do IBOV {data: preço}.
    
    Returns:
        dict: Retorno acumulado do IBOV (ibov_return_dict).
    """
    ibov_return_dict = {}
    if ibov:
        try:
            df_ibov = pd.Series(ibov)
            if df_ibov.empty or df_ibov.isna().all() or pd.isna(df_ibov.iloc[0]):
                print("IBOV vazio ou primeiro valor inválido, ignorando cálculo")
            else:
                ibov_return = (df_ibov / df_ibov.iloc[0] - 1) * 100
                ibov_return_dict = ibov_return.to_dict()
                print(f"IBOV return calculado com {len(ibov_return)} datas")
        except Exception as e:
            print(f"Erro ao calcular IBOV return: {e}")

    return ibov_return_dict

@measure_time
def calcular_metricas_tabela(tickers, quantities, portfolio, setor_pesos, start_date, end_date, dividends=None, get_sector_func=get_sector):
    """
    Calcula as métricas para a tabela (retorno total por ticker, pesos, etc.).
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        portfolio (dict): Dicionário de preços {ticker: {data: preço}}.
        setor_pesos (dict): Dicionário com os pesos por setor (por quantidade).
        start_date (str): Data inicial no formato 'YYYY-MM-DD'.
        end_date (str): Data final no formato 'YYYY-MM-DD'.
        dividends (dict, optional): Dicionário de dividendos por ticker.
    
    Returns:
        list: Lista de dicionários com as métricas para a tabela.
    """
    # [OTIMIZAÇÃO 1]: Pré-calcular setores para todos os tickers em um único dict
    # Evita chamadas repetitivas a get_sector dentro do loop, reduzindo overhead
    sectores = {ticker: get_sector_func(ticker) for ticker in tickers}
    
    # Inicializar variáveis
    soma_quantidades = sum(quantities)
    retorno_carteira = 0.0
    ganho_carteira = 0.0
    proventos_carteira = 0.0

    # Calcular ganhos e proventos (mantido como está, já otimizado)
    ganhos_proventos = calcular_ganhos_e_proventos(tickers, quantities, portfolio, start_date, end_date, dividends=dividends)

    # [OTIMIZAÇÃO 2]: Criar DataFrame diretamente com todos os dados necessários
    # Evita loops iniciais, usando list comprehensions e acesso direto a ganhos_proventos
    data = {
        'ticker': tickers,
        'quantidade': quantities,
        'preco_inicial': [obter_preco_inicial_e_final(portfolio[t])[0] if t in portfolio and portfolio[t] else None for t in tickers],
        'preco_final': [obter_preco_inicial_e_final(portfolio[t])[1] if t in portfolio and portfolio[t] else None for t in tickers],
        'setor': [sectores[t] for t in tickers],
        'ganho_capital': [ganhos_proventos[t]['ganho_capital'] if t in ganhos_proventos else 0.0 for t in tickers],
        'proventos': [ganhos_proventos[t]['proventos'] if t in ganhos_proventos else 0.0 for t in tickers]
    }
    df = pd.DataFrame(data)

    # [OTIMIZAÇÃO 3]: Calcular retornos e pesos vetorialmente com verificação simplificada
    # Usa where para tratar None/NaN, eliminando verificações redundantes
    df['retorno_total'] = ((df['preco_final'] - df['preco_inicial']) / df['preco_inicial'] * 100).where(
        df['preco_inicial'].notnull() & df['preco_final'].notnull(), None
    )
    df['peso_quantidade'] = df['quantidade'] / soma_quantidades * 100

    # [OTIMIZAÇÃO 4]: Calcular retorno da carteira com operação vetorial
    # Evita loop adicional, usa soma ponderada direta
    valid_retornos = df[df['retorno_total'].notnull()]
    if not valid_retornos.empty:
        retorno_carteira = (valid_retornos['retorno_total'] * valid_retornos['quantidade'] / soma_quantidades).sum()

    # Somar ganhos e proventos (já vetorial)
    ganho_carteira = df['ganho_capital'].sum()
    proventos_carteira = df['proventos'].sum()

    # [OTIMIZAÇÃO 5]: Construir ticker_metrics com apply em vez de loop
    # Reduz overhead de iteração, formata strings diretamente
    ticker_metrics = df.apply(lambda row: {
        'ticker': row['ticker'],
        'retorno_total': f"{row['retorno_total']:.2f}%" if pd.notnull(row['retorno_total']) else "N/A",
        'quantidade': row['quantidade'],
        'peso_quantidade_percentual': f"{row['peso_quantidade']:.2f}%",
        'setor': row['setor'],
        'ganho_capital': f"R$ {row['ganho_capital']:.2f}" if pd.notnull(row['ganho_capital']) else "N/A",
        'proventos': f"R$ {row['proventos']:.2f}" if pd.notnull(row['proventos']) else "N/A"
    }, axis=1).tolist()

    # [OTIMIZAÇÃO 6]: Adicionar linha de total com formatação direta
    # Evita verificações redundantes, usa valores calculados
    ticker_metrics.append({
        'ticker': 'Total',
        'retorno_total': f"{retorno_carteira:.2f}%" if retorno_carteira != 0 else "N/A",
        'quantidade': soma_quantidades,
        'peso_quantidade_percentual': "100.00%",
        'setor': '',
        'ganho_capital': f"R$ {ganho_carteira:.2f}" if ganho_carteira != 0 else "N/A",
        'proventos': f"R$ {proventos_carteira:.2f}" if proventos_carteira != 0 else "N/A"
    })

    return ticker_metrics

@measure_time
def calcular_ganhos_e_proventos(tickers, quantities, portfolio, start_date, end_date, dividends=None):
    """
    Calcula o ganho de capital e os proventos (dividendos) para cada ticker no período especificado.
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        portfolio (dict): Dicionário de preços {ticker: {data: preço}}.
        start_date (str): Data inicial no formato 'YYYY-MM-DD'.
        end_date (str): Data final no formato 'YYYY-MM-DD'.
    
    Returns:
        dict: Dicionário com {ticker: {'ganho_capital': float, 'proventos': float}}.
              - ganho_capital: Ganho de capital (valor final - valor inicial).
              - proventos: Total de dividendos recebidos no período.
    """
    resultados = {}
    
    for i, ticker in enumerate(tickers):
        quantidade = quantities[i]
        ganho_capital = 0.0
        proventos = 0.0
        
        # Calcular ganho de capital
        if ticker in portfolio and portfolio[ticker]:
            precos = portfolio[ticker]
            preco_inicial, preco_final = obter_preco_inicial_e_final(precos)
            if preco_inicial is not None and preco_final is not None:
                ganho_capital = (preco_final - preco_inicial) * quantidade
            else:
                ganho_capital = 0.0
        else:
            ganho_capital = 0.0
        
        # Calcular proventos (dividendos)
        if dividends is None or ticker not in dividends:
            print(f"Aviso: Dividendos não encontrados para {ticker} no store. Definindo proventos como 0.0.")
            proventos = 0.0
        else:
            dividends_data = pd.Series(dividends[ticker])
            if not dividends_data.empty:
                proventos = dividends_data.sum() * quantidade
            else:
                proventos = 0.0
        
        
        resultados[ticker] = {
            'ganho_capital': ganho_capital,
            'proventos': proventos
        }
    
    return resultados

@measure_time
def calcular_metricas(portfolio, tickers, quantities, start_date, end_date, ibov=None, dividends=None, get_sector_func=get_sector):

    """
    Calcula métricas do portfólio, incluindo tabela, retornos e pesos por setor.
    
    Args:
        portfolio (dict): Dicionário de preços {ticker: {data: preço}}.
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        start_date (str): Data inicial no formato 'YYYY-MM-DD'.
        end_date (str): Data final no formato 'YYYY-MM-DD'.
        ibov (dict, optional): Dicionário de preços do IBOV {data: preço}.
    
    Returns:
        dict: Dicionário com todas as métricas calculadas:
            - table_data: Métricas para a tabela.
            - portfolio_return: Retornos acumulados do portfólio.
            - individual_returns: Retornos acumulados por ticker.
            - portfolio_daily_return: Retornos diários do portfólio.
            - individual_daily_returns: Retornos diários por ticker.
            - ibov_return: Retorno acumulado do IBOV (se fornecido).
            - portfolio_values: Valores do portfólio ao longo do tempo.
            - setor_pesos: Pesos por setor (por quantidade).
            - setor_pesos_financeiros: Pesos por setor (por valor financeiro).
    """
    # Validação inicial
    if not tickers or not quantities or len(tickers) != len(quantities):
        print("Erro: tickers e quantities devem ter o mesmo tamanho e não podem estar vazios")
        return {
            'table_data': [],
            'portfolio_return': {},
            'individual_returns': {},
            'portfolio_daily_return': {},
            'individual_daily_returns': {},
            'ibov_return': {},
            'portfolio_values': {},
            'setor_pesos': {setor: 0.0 for setor in SETORES},
            'setor_pesos_financeiros': {setor: 0.0 for setor in SETORES}
        }

    if not portfolio:
        print("Erro: portfolio está vazio")
        return {
            'table_data': [],
            'portfolio_return': {},
            'individual_returns': {},
            'portfolio_daily_return': {},
            'individual_daily_returns': {},
            'ibov_return': {},
            'portfolio_values': {},
            'setor_pesos': {setor: 0.0 for setor in SETORES},
            'setor_pesos_financeiros': {setor: 0.0 for setor in SETORES}
        }

    # Passo 1: Calcular pesos por setor
    setor_pesos, setor_pesos_financeiros = calcular_pesos_por_setor(tickers, quantities, portfolio, get_sector_func=get_sector_func)

    # Passo 2: Calcular métricas da tabela
    ticker_metrics = calcular_metricas_tabela(tickers, quantities, portfolio, setor_pesos, start_date, end_date, dividends=dividends, get_sector_func=get_sector_func)

    # Passo 3: Calcular retornos acumulados e diários por ticker
    individual_returns, individual_daily_returns = calcular_retornos_individuais(tickers, portfolio)

    # Passo 4: Calcular retornos acumulados e diários do portfólio
    portfolio_return, portfolio_daily_return = calcular_retornos_portfolio(tickers, quantities, portfolio)

    # Passo 5: Calcular valores do portfólio
    portfolio_values = calcular_valores_portfolio(tickers, quantities, portfolio)

    # Passo 6: Calcular retorno do IBOV (se fornecido)
    ibov_return = calcular_retorno_ibov(ibov)

    # Retornar todas as métricas
    return {
        'table_data': ticker_metrics,
        'portfolio_return': portfolio_return,
        'individual_returns': individual_returns,
        'portfolio_daily_return': portfolio_daily_return,
        'individual_daily_returns': individual_daily_returns,
        'ibov_return': ibov_return,
        'portfolio_values': portfolio_values,
        'setor_pesos': setor_pesos,
        'setor_pesos_financeiros': setor_pesos_financeiros
    }

