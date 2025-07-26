from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from Findash.utils.logging_tools import logger
from .utils import measure_time

# Função auxiliar para garantir índice datetime
def ensure_datetime_index(series: pd.Series) -> pd.Series:
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index)
    return series

# Função auxiliar para calcular drawdown 
def calcular_max_drawdown(retornos: pd.Series) -> float:
    cum_returns = (1 + retornos).cumprod()
    drawdown = (cum_returns / cum_returns.cummax()) - 1
    return drawdown.min() if not drawdown.empty else 0

# Função auxiliar para formatar períodos
def formatar_periodo(ts: pd.Timestamp, tipo: str) -> str:
    if tipo == 'mensal':
        return ts.strftime('%Y-%m')
    elif tipo == 'trimestral':
        return f"{ts.year}-Q{(ts.month - 1) // 3 + 1}"
    elif tipo == 'semestral':
        return f"{ts.year}-S{(ts.month - 1) // 6 + 1}"
    elif tipo == 'anual':
        return str(ts.year)
    return str(ts)

@measure_time
def calcular_kpis(portfolio_daily_returns, benchmark_daily_returns=None):
    """
    Calcula KPIs financeiros manualmente.

    Args:
        portfolio_daily_returns (pd.Series): Retornos diários do portfólio.
        benchmark_daily_returns (pd.Series): Retornos diários do benchmark (opcional).

    Returns:
        dict: KPIs financeiros (sharpe, sortino, volatilidade, max_drawdown, retorno_medio_anual, alpha, beta).
    """
    portfolio_daily_returns = ensure_datetime_index(portfolio_daily_returns)
    if benchmark_daily_returns is not None:
        benchmark_daily_returns = ensure_datetime_index(benchmark_daily_returns)

    retorno_medio_anual = portfolio_daily_returns.mean() * 252
    volatilidade = portfolio_daily_returns.std(ddof=1) * np.sqrt(252)
    sharpe = retorno_medio_anual / volatilidade if not np.isclose(volatilidade, 0) else np.nan

    retornos_negativos = portfolio_daily_returns[portfolio_daily_returns < 0]
    downside_deviation = (
        np.sqrt(np.sum(retornos_negativos ** 2) / len(portfolio_daily_returns)) * np.sqrt(252)
        if len(retornos_negativos) > 0 else 0
    )
    sortino = retorno_medio_anual / downside_deviation if not np.isclose(downside_deviation, 0) else np.nan

    max_drawdown = calcular_max_drawdown(portfolio_daily_returns)

    metrics = {
        'sharpe': sharpe,
        'sortino': sortino,
        'volatilidade': volatilidade,
        'max_drawdown': max_drawdown,
        'retorno_medio_anual': retorno_medio_anual,
    }

    if benchmark_daily_returns is not None:
        combined = pd.concat([portfolio_daily_returns, benchmark_daily_returns], axis=1).dropna()
        portfolio_ret = combined.iloc[:, 0]
        benchmark_ret = combined.iloc[:, 1]

        cov_matrix = np.cov(portfolio_ret, benchmark_ret)
        beta = cov_matrix[0, 1] / cov_matrix[1, 1] if not np.isclose(cov_matrix[1, 1], 0) else np.nan
        alpha = portfolio_ret.mean() - beta * benchmark_ret.mean() if not np.isnan(beta) else np.nan

        metrics['alpha'] = alpha * 252
        metrics['beta'] = beta

    return metrics

@measure_time
def calcular_kpis_por_periodo(portfolio_daily_returns, period: str, benchmark_daily_returns=None):
    """
    Calcula KPIs financeiros por período (mensal, trimestral, semestral, anual).

    Args:
        portfolio_daily_returns (pd.Series): Retornos diários do portfólio.
        period (str): Período para agrupamento ('mensal', 'trimestral', 'semestral', 'anual').
        benchmark_daily_returns (pd.Series): Retornos diários do benchmark (opcional).

    Returns:
        pd.DataFrame: KPIs nas linhas, períodos nas colunas.
    """
    portfolio_daily_returns = ensure_datetime_index(portfolio_daily_returns)
    if benchmark_daily_returns is not None:
        benchmark_daily_returns = ensure_datetime_index(benchmark_daily_returns)

    period_map = {
        'mensal': 'ME',
        'trimestral': 'QE',
        'semestral': '6ME',
        'anual': 'YE'
    }

    if period not in period_map:
        raise ValueError("Período deve ser 'mensal', 'trimestral', 'semestral' ou 'anual'")

    freq = period_map[period]
    grouped_returns = portfolio_daily_returns.groupby(pd.Grouper(freq=freq))
    grouped_keys = list(grouped_returns.groups.keys())
    if not grouped_keys:
        return pd.DataFrame()

    grouped_benchmark = (
        benchmark_daily_returns.groupby(pd.Grouper(freq=freq))
        if benchmark_daily_returns is not None else None
    )

    # Pega os KPIs diretamente de uma execução modelo para evitar inconsistência futura
    kpis_exemplo = calcular_kpis(pd.Series([0.0]), pd.Series([0.0]))
    kpis = list(kpis_exemplo.keys())

    # Geração das colunas com função auxiliar
    columns = [formatar_periodo(pd.Timestamp(g), period) for g in grouped_keys]
    result = pd.DataFrame(index=kpis, columns=columns)

    for name, group in grouped_returns:
        period_label = formatar_periodo(pd.Timestamp(name), period)
        benchmark_group = (
            grouped_benchmark.get_group(name) if benchmark_daily_returns is not None and name in grouped_benchmark.groups else None
        )
        period_metrics = calcular_kpis(group, benchmark_group)

        for kpi in kpis:
            result.loc[kpi, period_label] = period_metrics.get(kpi, np.nan)

    return result.astype(float).round(4)
    