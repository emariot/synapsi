import pandas as pd
import numpy as np
from .utils import measure_time

@measure_time
def calcular_retornos_individuais(tickers: list[str], precos_df: pd.DataFrame) -> tuple[dict[str, dict], dict[str, dict]]:
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
def calcular_retornos_portfolio(tickers: list[str], quantities: list[float], portfolio_values: pd.DataFrame) -> tuple[dict[str, float], dict[str, float]]:
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

    portfolio_return = (portfolio_total / portfolio_total.iloc[0] - 1) * 100
    portfolio_return_dict = portfolio_return.to_dict()

    portfolio_daily_return = portfolio_total.pct_change() * 100
    portfolio_daily_return_dict = portfolio_daily_return.dropna().to_dict()

    return portfolio_return_dict, portfolio_daily_return_dict

@measure_time
def calcular_retorno_ibov(ibov: dict) -> dict:
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

def calcular_retorno_diario_ibov(ibov: dict) -> pd.Series:
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