from typing import List, Dict, Any
from redis import Redis
import yfinance as yf
import pandas as pd
import time
from Findash.services.ticker_service import manage_ticker_data, get_all_sectors, get_sector, DATABASE_PATH
from Findash.utils.logging_tools import logger
from .utils import measure_time

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
    normalized_tickers = [ticker if ticker == '^BVSP' else f"{ticker}.SA" if not ticker.endswith('.SA') else ticker for ticker in tickers]
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