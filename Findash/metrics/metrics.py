from typing import List, Dict, Any, Optional
import pandas as pd
from redis import Redis
from Findash.utils.logging_tools import logger
from Findash.services.ticker_service import get_all_sectors, get_sector
from .returns import calcular_retornos_individuais, calcular_retornos_portfolio, calcular_retorno_ibov, calcular_retorno_diario_ibov
from .metrics_calc import calcular_pesos_por_setor, calcular_metricas_tabela
from .kpis_calc import calcular_kpis, calcular_kpis_por_periodo
from .utils import measure_time

@measure_time
def calcular_metricas(portfolio: Dict[str, Any], tickers: List[str], quantities: List[float], 
                      start_date: str, end_date: str, empresas_redis: Redis, 
                      ibov: Optional[Dict[str, float]] = None, 
                      dividends: Optional[Dict[str, Any]] = None,
                      period: str = 'mensal'
                      ) -> Dict[str, Any]:
    """
    Calcula métricas do portfólio, incluindo tabela, retornos e pesos por setor.
    
    Args:
        portfolio (dict): Dicionário de preços {ticker: {data: preço}}.
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        start_date (str): Data inicial no formato 'YYYY-MM-DD'.
        end_date (str): Data final no formato 'YYYY-MM-DD'.
        empresas_redis (redis.Redis): Conexão Redis para dados de empresas (DB3).
        ibov (dict, optional): Dicionário de preços do IBOV {data: preço}.
        dividends (dict, optional): Dicionário de dividendos por ticker.
        period (str, optional): Período para KPIs ('mensal', 'trimestral', 'semestral', 'anual'). Padrão: 'mensal'.
    
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
            - kpis_por_periodo: KPIs por período (DataFrame com KPIs nas linhas, períodos nas colunas).
    """
    sectors_data = get_all_sectors(empresas_redis)
    setores_economicos = sectors_data['setores_economicos']
    ticker_to_setor = sectors_data['ticker_to_setor']

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
            'kpis': {},
            'kpis_por_periodo': pd.DataFrame()
        }
    if not empresas_redis:
        logger.error("[calcular_metricas] empresas_redis não fornecido")
        raise ValueError("Conexão Redis (empresas_redis) é obrigatória")

    precos_df = pd.DataFrame(portfolio)
    precos_df = precos_df[tickers]
    precos_df.index = pd.to_datetime(precos_df.index).strftime('%Y-%m-%d')

    quantities_dict = dict(zip(tickers, quantities))
    portfolio_values = precos_df * pd.Series(quantities_dict)
    portfolio_values_dict = portfolio_values.to_dict()

    sectores = {}
    for ticker in tickers:
        sector = ticker_to_setor.get(ticker)
        if not sector:
            logger.warning(f"[calcular_metricas] Ticker {ticker} não encontrado em ticker_to_setor, usando get_sector")
            sector = get_sector(ticker, empresas_redis)
        sectores[ticker] = sector or ''

    setor_pesos, setor_pesos_financeiros = calcular_pesos_por_setor(
        tickers, quantities, precos_df, setores_economicos, sectores
    )
    
    ticker_metrics = calcular_metricas_tabela(tickers, quantities, precos_df, dividends, sectores)

    individual_returns, individual_daily_returns = calcular_retornos_individuais(tickers, precos_df)
    individual_returns = {
        ticker: [{'x': k, 'y': v} for k, v in returns.items()]
        for ticker, returns in individual_returns.items()
    }

    portfolio_return, portfolio_daily_return = calcular_retornos_portfolio(tickers, quantities, portfolio_values)
    portfolio_return = [
        {'x': k, 'y': v}
        for k, v in portfolio_return.items()
    ]

    ibov_return = calcular_retorno_ibov(ibov)
    ibov_return = [
        {'x': pd.to_datetime(k).strftime('%Y-%m-%d'), 'y': v}
        for k, v in ibov_return.items()
    ]

    portfolio_returns_series = pd.Series(portfolio_daily_return).sort_index()
    portfolio_returns_series.index = pd.to_datetime(portfolio_returns_series.index)
    portfolio_returns_series = portfolio_returns_series / 100

    benchmark_returns_series = None
    if ibov:
        benchmark_returns_series = calcular_retorno_diario_ibov(ibov)
        benchmark_returns_series = benchmark_returns_series.loc[portfolio_returns_series.index]

    kpis = calcular_kpis(portfolio_returns_series, benchmark_returns_series)
    logger.info("KPIs calculados: " + ", ".join(f"{k}: {v:.4f}" for k, v in kpis.items()))

    kpis_por_periodo = calcular_kpis_por_periodo(portfolio_returns_series, period, benchmark_returns_series)
    logger.info(f"KPIs por período ({period}) calculados: {kpis_por_periodo.shape}")

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
        'kpis': kpis,
        'kpis_por_periodo': kpis_por_periodo
    }