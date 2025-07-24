from typing import List, Dict, Any, Optional
from redis import Redis
import yfinance as yf
import pandas as pd
import numpy as np
import time
import functools
from datetime import datetime
from Findash.services.ticker_service import manage_ticker_data, get_all_sectors, get_sector, DATABASE_PATH
from Findash.utils.logging_tools import logger 

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


@measure_time
def obter_dados(tickers: List[str], start_date: str, end_date: str, include_ibov: bool = True) -> Dict[str, Any]:
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
    # Normalizar tickers para yfinance (adicionar .SA se necessário)
    normalized_tickers = [ticker if ticker == '^BVSP' else f"{ticker}.SA" if not ticker.endswith('.SA') else ticker for ticker in tickers]
    # Mapear tickers normalizados para originais
    ticker_map = {ticker if ticker == '^BVSP' else f"{ticker}.SA" if not ticker.endswith('.SA') else ticker: ticker.replace('.SA', '') for ticker in tickers}
    
    result = {'portfolio': {ticker_map.get(t, t): {} for t in normalized_tickers}, 'ibov': {}, 'dividends': {ticker_map.get(t, t): {} for t in normalized_tickers}}
    valid_tickers = []

    tickers_to_download = normalized_tickers + ['^BVSP'] if include_ibov else normalized_tickers

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
                logger.warning(f"'Adj Close' não encontrado para {tickers_to_download}")
                return result
            adj_close = data['Adj Close']

            if 'Dividends' in available_columns:
                dividends_data = data['Dividends']
            else:
                logger.info("Nenhum dado de dividendos retornado pelo yfinance")
                dividends_data = None

            valid_tickers = [t for t in normalized_tickers if t in adj_close.columns and not adj_close[t].isna().all()]
            if valid_tickers:
                adj_close_portfolio = adj_close[valid_tickers]
                print(f"Portfolio: {len(adj_close_portfolio)} linhas para {valid_tickers}")
                adj_close_portfolio.index = adj_close_portfolio.index.map(lambda x: x.strftime('%Y-%m-%d'))
                # Remover .SA das chaves ao preencher result['portfolio']
                result['portfolio'].update({ticker_map.get(ticker, ticker): adj_close_portfolio[ticker].to_dict() for ticker in valid_tickers})
            else:
                print(f"Nenhum dado válido para {normalized_tickers}")

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
                        # Remover .SA das chaves ao preencher result['dividends']
                        result['dividends'][ticker_map.get(ticker, ticker)] = ticker_dividends.to_dict()
                    else:
                        result['dividends'][ticker] = {}
            else:
                for ticker in valid_tickers:
                    result['dividends'][ticker] = {}

        except Exception as e:
            print(f"Erro ao obter dados do yfinance: {e}")
            for ticker in normalized_tickers:
                result['portfolio'][ticker] = {}
                result['dividends'][ticker] = {}
            if include_ibov:
                result['ibov'] = {}

    return result

# Funções menores para cada tipo de cálculo
@measure_time
def calcular_pesos_por_setor(tickers: List[str], quantities: List[float], precos_df:pd.DataFrame, 
                             setores_economicos: List[str], sectores: Dict[str, str]) -> tuple[Dict[str, float], Dict[str, float]]:
    """
    Calcula os pesos por setor com base na quantidade e no valor financeiro.
    Alteração: Recebe empresas_redis como parâmetro para passar para get_sector.
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        precos_df (DataFrame): DataFrame com preços, tickers como colunas, índice como string 'YYYY-MM-DD'.
        setores_economicos (list): Lista de setores econômicos pré-carregada.
        sectores (dict): Dicionário de setores {ticker: setor}.
    
    Returns:
        tuple: (setor_pesos, setor_pesos_financeiros), dicionários com os pesos por setor.
    """
    # Inicializar dicionários de pesos por setor
    setor_pesos = {setor: 0.0 for setor in setores_economicos}
    setor_pesos_financeiros = {setor: 0.0 for setor in setores_economicos}

    # Criar DataFrame com dados necessários
    df = pd.DataFrame({
        'ticker': tickers,
        'quantidade': quantities,
        'preco_final': precos_df.iloc[-1].reindex(tickers) if not precos_df.empty else pd.Series(index=tickers, dtype=float),
        'setor': [sectores.get(t, '') for t in tickers]
    })
    # Filtrar tickers válidos (com preço final não nulo)
    df = df[df['preco_final'].notnull()]
    if df.empty:
        return setor_pesos, setor_pesos_financeiros

    # Calcular soma total das quantidades
    soma_quantidades = df['quantidade'].sum()

    # Calcular pesos por quantidade vetorialmente
    df['peso_quantidade'] = df['quantidade'] / soma_quantidades * 100
    setor_pesos.update(df.groupby('setor')['peso_quantidade'].sum().to_dict())

    # Calcular valor financeiro total
    df['valor_financeiro'] = df['quantidade'] * df['preco_final']
    valor_total = df['valor_financeiro'].sum()

    # Calcular pesos financeiros vetorialmente
    if valor_total > 0:
        df['peso_financeiro'] = df['valor_financeiro'] / valor_total * 100
        setor_pesos_financeiros.update(df.groupby('setor')['peso_financeiro'].sum().to_dict())

    return setor_pesos, setor_pesos_financeiros

@measure_time
def calcular_retornos_individuais(tickers: List[str], 
                                  precos_df: pd.DataFrame) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Calcula os retornos acumulados e diários para cada ticker.
    
    Args:
        tickers (list): Lista de tickers.
        precos_df (DataFrame): DataFrame com preços, tickers como colunas.
    
    Returns:
        tuple: (individual_returns_dict, individual_daily_returns_dict)
            - individual_returns_dict: Retornos acumulados por ticker.
            - individual_daily_returns_dict: Retornos diários por ticker.
    """
    if precos_df.empty or precos_df.shape[0] == 0:
        print("Nenhum dado válido para calcular retornos individuais")
        return (
            {ticker: {} for ticker in tickers},
            {ticker: {} for ticker in tickers}
        )

    individual_returns_df = (precos_df / precos_df.iloc[0] - 1) * 100
    individual_returns_dict = {
        ticker: individual_returns_df[ticker].to_dict()
        for ticker in tickers if ticker in individual_returns_df.columns
    }

    daily_returns_df = precos_df.pct_change(fill_method=None) * 100
    individual_daily_returns_dict = {
        ticker: daily_returns_df[ticker].dropna().to_dict()
        for ticker in tickers if ticker in daily_returns_df.columns
    }

    return individual_returns_dict, individual_daily_returns_dict

@measure_time
def calcular_retornos_portfolio(tickers:List[str], quantities:List[float], 
                                portfolio_values:pd.DataFrame) -> tuple[Dict[str,float], Dict[str,float]]:
    """
    Calcula os retornos acumulados e diários do portfólio.
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        portfolio_values (DataFrame): DataFrame com valores do portfólio (precos_df * quantities), índice como string 'YYYY-MM-DD'.
    
    Returns:
        tuple: (portfolio_return_dict, portfolio_daily_return_dict)
            - portfolio_return_dict: Retornos acumulados do portfólio.
            - portfolio_daily_return_dict: Retornos diários do portfólio.
    """
    portfolio_total = portfolio_values.sum(axis=1)

    # Retornos acumulados
    portfolio_return = (portfolio_total / portfolio_total.iloc[0] - 1) * 100
    portfolio_return_dict = portfolio_return.to_dict()

    # Retornos diários
    portfolio_daily_return = portfolio_total.pct_change() * 100
    portfolio_daily_return_dict = portfolio_daily_return.dropna().to_dict()

    return portfolio_return_dict, portfolio_daily_return_dict

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


def calcular_retorno_diario_ibov(ibov):
    """
    Calcula os retornos diários do IBOV em formato decimal, com índice datetime.

    Args:
        ibov (dict): Dicionário de preços do IBOV {data: preço}.

    Returns:
        pd.Series: Série de retornos diários do IBOV com índice datetime.
    """
    if not ibov:
        return pd.Series(dtype=float)

    try:
        df_ibov = pd.Series(ibov)
        df_ibov.index = pd.to_datetime(df_ibov.index)
        df_ibov = df_ibov.sort_index()
        
        if df_ibov.empty or df_ibov.isna().all() or pd.isna(df_ibov.iloc[0]):
            print("IBOV vazio ou primeiro valor inválido, ignorando cálculo")
            return pd.Series(dtype=float)

        ibov_daily_returns = df_ibov.pct_change().dropna()
        return ibov_daily_returns

    except Exception as e:
        print(f"Erro ao calcular retorno diário do IBOV: {e}")
        return pd.Series(dtype=float)

@measure_time
def calcular_metricas_tabela(tickers: List[str], quantities: List[float], precos_df: pd.DataFrame, 
                             dividends:Optional[Dict[str, Any]]=None, sectores: Dict[str,str]=None) -> List[Dict[str, Any]]:
    """
    Calcula métricas da tabela de forma eficiente.
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        portfolio_df (DataFrame): DataFrame com preços, ganhos e proventos por ticker.
        sectores (dict, optional): Dicionário de setores {ticker: setor}.
    
    Returns:
        list: Lista de dicionários com as métricas para a tabela, com valores numéricos puros.
    """
    # Extrair preços inicial e final vetorialmente em um único passo
    quantities_series = pd.Series(quantities, index=tickers)
    preco_inicial = precos_df.iloc[0].reindex(tickers) if not precos_df.empty else pd.Series(index=tickers, dtype=float)
    preco_final = precos_df.iloc[-1].reindex(tickers) if not precos_df.empty else pd.Series(index=tickers, dtype=float)

    # Calcular ganho de capital vetorialmente
    ganho_capital = ((preco_final - preco_inicial) * quantities_series).fillna(0.0)
    # Calcular proventos
    proventos = pd.Series({
        t: sum(dividends[t].values()) * quantities_series[t]
        for t in tickers if t in dividends
    }).reindex(tickers, fill_value=0.0)

    # Criar DataFrame com todos os dados
    df = pd.DataFrame({
        'ticker': tickers,
        'quantidade': quantities,
        'preco_inicial': preco_inicial,
        'preco_final': preco_final,
        'setor': [sectores.get(t,'') for t in tickers],
        'ganho_capital': ganho_capital,
        'proventos': proventos
    })

    # Calcular retorno total e peso por quantidade vetorialmente
    df['retorno_total'] = ((df['preco_final'] - df['preco_inicial']) / df['preco_inicial'] * 100).where(
        df['preco_inicial'].notnull() & df['preco_final'].notnull(), None
    )
    soma_quantidades = df['quantidade'].sum()
    df['peso_quantidade_percentual'] = df['quantidade'] / soma_quantidades * 100 if soma_quantidades > 0 else 0.0

    # Substituir NaN por None (para serialização amigável)
    df[['retorno_total', 'ganho_capital', 'proventos']] = df[['retorno_total', 'ganho_capital', 'proventos']].where(
        df[['retorno_total', 'ganho_capital', 'proventos']].notnull(), None
    )

    # Selecionar colunas desejadas e transformar em lista de dicionários
    ticker_metrics = df[[
        'ticker', 'retorno_total', 'quantidade', 'peso_quantidade_percentual',
        'setor', 'ganho_capital', 'proventos'
    ]].to_dict(orient='records')
    # Adicionar linha de total
    retorno_carteira = (
        (df[df['retorno_total'].notnull()]['retorno_total'] * df['quantidade']) / soma_quantidades
    ).sum() if soma_quantidades > 0 else 0.0

    ticker_metrics.append({
            'ticker': 'Total',
            'retorno_total': retorno_carteira if retorno_carteira != 0 else None,
            'quantidade': soma_quantidades,
            'peso_quantidade_percentual': 100.0,
            'setor': '',
            'ganho_capital': df['ganho_capital'].sum() or None,
            'proventos': df['proventos'].sum() or None
    })

    return ticker_metrics

@measure_time
def calcular_kpis_quantstats(portfolio_daily_returns, benchmark_daily_returns=None):
    """
    Calcula KPIs financeiros manualmente.

    Args:
        portfolio_daily_returns (pd.Series): Retornos diários do portfólio.
        benchmark_daily_returns (pd.Series): Retornos diários do benchmark (opcional).

    Returns:
        dict: KPIs financeiros (sharpe, sortino, volatilidade, max_drawdown, retorno_medio_anual, alpha, beta).
    """

    # Garantir que o índice seja datetime
    if not isinstance(portfolio_daily_returns.index, pd.DatetimeIndex):
        portfolio_daily_returns.index = pd.to_datetime(portfolio_daily_returns.index)

    if benchmark_daily_returns is not None and not isinstance(benchmark_daily_returns.index, pd.DatetimeIndex):
        benchmark_daily_returns.index = pd.to_datetime(benchmark_daily_returns.index)

    # Calcular retorno médio anual
    retorno_medio_anual = portfolio_daily_returns.mean() * 252

    # Calcular volatilidade
    volatilidade = np.std(portfolio_daily_returns, ddof=1) * np.sqrt(252)

    # Calcular Sharpe Ratio (taxa livre de risco = 0)
    sharpe = retorno_medio_anual / volatilidade if volatilidade != 0 else np.nan

    # Calcular Sortino Ratio
    retornos_negativos = portfolio_daily_returns[portfolio_daily_returns < 0]  # Excluir zeros
    downside_deviation = np.sqrt(np.sum(retornos_negativos ** 2) / len(portfolio_daily_returns)) * np.sqrt(252) if len(retornos_negativos) > 0 else 0
    sortino = retorno_medio_anual / downside_deviation if downside_deviation != 0 else np.nan

    # Calcular Max Drawdown
    cum_returns = (1 + portfolio_daily_returns).cumprod()
    rolling_max = cum_returns.cummax()
    drawdowns = (cum_returns - rolling_max) / rolling_max
    max_drawdown = drawdowns.min() if not drawdowns.empty else 0

    # Inicializar dicionário de métricas
    metrics = {
        'sharpe': sharpe,
        'sortino': sortino,
        'volatilidade': volatilidade,
        'max_drawdown': max_drawdown,
        'retorno_medio_anual': retorno_medio_anual,
    }

    # Calcular alpha e beta (se benchmark disponível)
    if benchmark_daily_returns is not None:
        combined = pd.concat([portfolio_daily_returns, benchmark_daily_returns], axis=1).dropna()
        portfolio_ret = combined.iloc[:, 0]
        benchmark_ret = combined.iloc[:, 1]

        # Regressão linear: retorno_portfolio = alpha + beta * retorno_benchmark
        cov_matrix = np.cov(portfolio_ret, benchmark_ret)
        beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else np.nan
        alpha = portfolio_ret.mean() - beta * benchmark_ret.mean() if not np.isnan(beta) else np.nan

        metrics['alpha'] = alpha * 252  # anualizar
        metrics['beta'] = beta

    return metrics

@measure_time
def calcular_metricas(portfolio: Dict[str, Any], tickers: List[str], quantities: List[float], 
                      start_date:str, end_date:str, empresas_redis: Redis, ibov: Optional[Dict[str,float]]=None, 
                      dividends: Optional[Dict[str,Any]]=None) -> Dict[str, Any]:

    """
    Calcula métricas do portfólio, incluindo tabela, retornos e pesos por setor.
    
    Args:
        portfolio (dict): Dicionário de preços {ticker: {data: preço}}.
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        start_date (str): Data inicial no formato 'YYYY-MM-DD'.
        end_date (str): Data final no formato 'YYYY-MM-DD'.
        ibov (dict, optional): Dicionário de preços do IBOV {data: preço}.
        empresas_redis (redis.Redis): Conexão Redis para dados de empresas (DB3).
    
    Returns:
        dict: Dicionário com todas as métricas calculadas:
            - table_data: Métricas para a tabela.
            - portfolio_return: Lista de {x: data, y: retorno} para o portfólio.
            - individual_returns: Retornos acumulados por ticker.
            - portfolio_daily_return: Retornos diários do portfólio.
            - individual_daily_returns: Retornos diários por ticker.
            - ibov_return: Lista de {x: data, y: retorno} para o IBOV (se fornecido).
            - portfolio_values: Valores do portfólio ao longo do tempo.
            - setor_pesos: Pesos por setor (por quantidade).
            - setor_pesos_financeiros: Pesos por setor (por valor financeiro).
            - kpis: Indicadores financeiros.
    """
    # Pré-carregar setores econômicos antes da validação
    sectors_data = get_all_sectors(empresas_redis)
    setores_economicos = sectors_data['setores_economicos']
    ticker_to_setor = sectors_data['ticker_to_setor']

    # Validação inicial
    if not tickers or not quantities or len(tickers) != len(quantities) or not portfolio:
        logger.error(f"[calcular_metricas] Entrada inválida: tickers={len(tickers)}, quantities={len(quantities)}, portfolio_vazio={not portfolio}")
        
        return {
            'table_data': [],
            'portfolio_return': {},
            'individual_returns': {},
            'portfolio_daily_return': {},
            'individual_daily_returns': {},
            'ibov_return': {},
            'portfolio_values': {},
            'setor_pesos': {setor: 0.0 for setor in setores_economicos},
            'setor_pesos_financeiros': {setor: 0.0 for setor in setores_economicos},
            'kpis': {}
        }
    if not empresas_redis:
        logger.error("[calcular_metricas] empresas_redis não fornecido")
        raise ValueError("Conexão Redis (empresas_redis) é obrigatória")
    
    # Converter portfolio em DataFrame uma vez
    precos_df = pd.DataFrame(portfolio)
    precos_df = precos_df[tickers]
    precos_df.index = pd.to_datetime(precos_df.index).strftime('%Y-%m-%d')

    # Calcular valores do portfólio uma vez
    quantities_dict = dict(zip(tickers, quantities))
    portfolio_values = precos_df * pd.Series(quantities_dict)
    portfolio_values_dict = portfolio_values.to_dict()

    # Calcular setores usar mapeamento ticker -> setor com fallback para get_sector
    sectores = {}
    for ticker in tickers:
        sector = ticker_to_setor.get(ticker)
        if not sector:
            logger.warning(f"[calcular_metricas] Ticker {ticker} não encontrado em ticker_to_setor, usando get_sector")
            sector = get_sector(ticker, empresas_redis)
        sectores[ticker] = sector or ''
    
    # Passo 1: Calcular pesos por setor
    setor_pesos, setor_pesos_financeiros = calcular_pesos_por_setor(
        tickers, quantities, precos_df, setores_economicos, sectores
        )
    
    # Passo 2: Calcular métricas da tabela
    ticker_metrics = calcular_metricas_tabela(tickers, quantities, precos_df, dividends, sectores)

    # Passo 3: Calcular retornos acumulados e diários por ticker
    individual_returns, individual_daily_returns = calcular_retornos_individuais(tickers, precos_df)
    # Formatar individual_returns para o gráfico
    individual_returns = {
        ticker: [{'x': k, 'y': v} for k, v in returns.items()]
        for ticker, returns in individual_returns.items()
    }
    # Passo 4: Calcular retornos acumulados e diários do portfólio
    portfolio_return, portfolio_daily_return = calcular_retornos_portfolio(tickers, quantities, portfolio_values)
    # Formatar portfolio_return para o gráfico
    portfolio_return = [
        {'x': k, 'y': v}
        for k, v in portfolio_return.items()
    ]

    # Passo 5: Calcular retorno do IBOV (se fornecido)
    ibov_return = calcular_retorno_ibov(ibov)
    ibov_return = [
        {'x': pd.to_datetime(k).strftime('%Y-%m-%d'), 'y': v}
        for k, v in ibov_return.items()
    ]

    # Passo 6: Clacular KPIs usando quantstats
    portfolio_returns_series = pd.Series(portfolio_daily_return).sort_index()
    portfolio_returns_series.index = pd.to_datetime(portfolio_returns_series.index)
    portfolio_returns_series = portfolio_returns_series / 100  # Converter de % para decimal

    benchmark_returns_series = None
    if ibov:
        benchmark_returns_series = calcular_retorno_diario_ibov(ibov)
        # Garantir alinhamento com o portfólio
        benchmark_returns_series = benchmark_returns_series.loc[portfolio_returns_series.index]

    kpis = calcular_kpis_quantstats(portfolio_returns_series, benchmark_returns_series)
    logger.info("KPIs calculados: " + ", ".join(f"{k}: {v:.4f}" for k, v in kpis.items()))

    # Retornar todas as métricas
    return {
        'table_data': ticker_metrics,
        'portfolio_return': portfolio_return,
        'individual_returns': individual_returns,
        'portfolio_daily_return': portfolio_daily_return,
        'individual_daily_returns': individual_daily_returns,
        'ibov_return': ibov_return,
        'portfolio_values': portfolio_values_dict,
        'setor_pesos': setor_pesos,
        'setor_pesos_financeiros': setor_pesos_financeiros,
        'kpis': kpis
    }

