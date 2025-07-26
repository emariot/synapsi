from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from Findash.utils.logging_tools import logger
from .utils import measure_time

@measure_time
def calcular_pesos_por_setor(tickers: List[str], quantities: List[float], precos_df: pd.DataFrame, 
                             setores_economicos: List[str], sectores: Dict[str, str]) -> tuple[Dict[str, float], Dict[str, float]]:
    """
    Calcula os pesos por setor com base na quantidade e no valor financeiro.
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        precos_df (DataFrame): DataFrame com preços, tickers como colunas, índice como string 'YYYY-MM-DD'.
        setores_economicos (list): Lista de setores econômicos pré-carregada.
        sectores (dict): Dicionário de setores {ticker: setor}.
    
    Returns:
        tuple: (setor_pesos, setor_pesos_financeiros), dicionários com os pesos por setor.
    """
    setor_pesos = {setor: 0.0 for setor in setores_economicos}
    setor_pesos_financeiros = {setor: 0.0 for setor in setores_economicos}

    df = pd.DataFrame({
        'ticker': tickers,
        'quantidade': quantities,
        'preco_final': precos_df.iloc[-1].reindex(tickers) if not precos_df.empty else pd.Series(index=tickers, dtype=float),
        'setor': [sectores.get(t, '') for t in tickers]
    })
    df = df[df['preco_final'].notnull()]
    if df.empty:
        return setor_pesos, setor_pesos_financeiros

    soma_quantidades = df['quantidade'].sum()
    df['peso_quantidade'] = df['quantidade'] / soma_quantidades * 100
    setor_pesos.update(df.groupby('setor')['peso_quantidade'].sum().to_dict())

    df['valor_financeiro'] = df['quantidade'] * df['preco_final']
    valor_total = df['valor_financeiro'].sum()
    if valor_total > 0:
        df['peso_financeiro'] = df['valor_financeiro'] / valor_total * 100
        setor_pesos_financeiros.update(df.groupby('setor')['peso_financeiro'].sum().to_dict())

    return setor_pesos, setor_pesos_financeiros

@measure_time
def calcular_metricas_tabela(tickers: List[str], quantities: List[float], precos_df: pd.DataFrame, 
                             dividends: Optional[Dict[str, Any]] = None, sectores: Dict[str, str] = None) -> List[Dict[str, Any]]:
    """
    Calcula métricas da tabela de forma eficiente.
    
    Args:
        tickers (list): Lista de tickers.
        quantities (list): Lista de quantidades correspondentes aos tickers.
        precos_df (DataFrame): DataFrame com preços, tickers como colunas.
        dividends (dict, optional): Dicionário de dividendos por ticker.
        sectores (dict, optional): Dicionário de setores {ticker: setor}.
    
    Returns:
        list: Lista de dicionários com as métricas para a tabela, com valores numéricos puros.
    """
    quantities_series = pd.Series(quantities, index=tickers)
    preco_inicial = precos_df.iloc[0].reindex(tickers) if not precos_df.empty else pd.Series(index=tickers, dtype=float)
    preco_final = precos_df.iloc[-1].reindex(tickers) if not precos_df.empty else pd.Series(index=tickers, dtype=float)

    ganho_capital = ((preco_final - preco_inicial) * quantities_series).fillna(0.0)
    proventos = pd.Series({
        t: sum(dividends[t].values()) * quantities_series[t]
        for t in tickers if t in dividends
    }).reindex(tickers, fill_value=0.0)

    df = pd.DataFrame({
        'ticker': tickers,
        'quantidade': quantities,
        'preco_inicial': preco_inicial,
        'preco_final': preco_final,
        'setor': [sectores.get(t, '') for t in tickers],
        'ganho_capital': ganho_capital,
        'proventos': proventos
    })

    df['retorno_total'] = ((df['preco_final'] - df['preco_inicial']) / df['preco_inicial'] * 100).where(
        df['preco_inicial'].notnull() & df['preco_final'].notnull(), None
    )
    soma_quantidades = df['quantidade'].sum()
    df['peso_quantidade_percentual'] = df['quantidade'] / soma_quantidades * 100 if soma_quantidades > 0 else 0.0

    df[['retorno_total', 'ganho_capital', 'proventos']] = df[['retorno_total', 'ganho_capital', 'proventos']].where(
        df[['retorno_total', 'ganho_capital', 'proventos']].notnull(), None
    )

    ticker_metrics = df[[
        'ticker', 'retorno_total', 'quantidade', 'peso_quantidade_percentual',
        'setor', 'ganho_capital', 'proventos'
    ]].to_dict(orient='records')
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
