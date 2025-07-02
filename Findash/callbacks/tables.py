from dash import Dash, Output, Input, no_update, State
from utils.serialization import orjson_loads, orjson_dumps
from Findash.utils.logging_tools import log_callback, logger

def register_table_callbacks(dash_app: Dash):
    @dash_app.callback(
        Output('data-store', 'data', allow_duplicate=True),
        Input('price-table', 'active_cell'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    @log_callback("delete_ticker")
    def delete_ticker(active_cell, store_data):
        """
        Remove um ticker do portfólio usando o PortfolioService.
        """
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not active_cell or not store_data or not store_data['tickers']:
            return no_update
        
        row = active_cell['row']
        col = active_cell['column_id']

        if col != 'acao' or row >= len(store_data['tickers']):
            return no_update
        
        ticker_to_remove = store_data['tickers'][row]
    
        try:
            updated_portfolio = dash_app.portfolio_service.remove_ticker(store_data, ticker_to_remove)
            logger.info(f"Ticker {ticker_to_remove} removido")

            # Só retorna se de fato alterou
            if updated_portfolio != store_data:
                return orjson_dumps(updated_portfolio).decode('utf-8')
            else:
                return no_update
        except ValueError as e:
            logger.error(f"Erro ao remover ticker: {e}")
            return no_update
        
    @dash_app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('ticker-dropdown', 'value'),
         Output('ticker-error-alert', 'children'),
         Output('ticker-error-alert', 'is_open'),
         Output('ticker-dropdown', 'disabled')],
        Input('ticker-dropdown', 'value'),
        State('data-store', 'data'),
        State('client-config', 'data'),
        prevent_initial_call=True
    )
    @log_callback("add_ticker")
    def add_ticker(selected_ticker, store_data, client_config):
        """
        Adiciona um ticker ao portfólio usando o PortfolioService, validando o limite de tickers.
        """
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not selected_ticker or not store_data:
            return no_update, None, no_update, no_update, no_update
        
        # Verificar limite de tickers
        tickers_limit = client_config.get('tickers_limit', 5)
        current_tickers = len(store_data['tickers'])
        if current_tickers >= tickers_limit:
            error_message = f"Limite de {tickers_limit} tickers atingido"
            logger.warning(error_message)
            return no_update, None, error_message, True, True
        
        try:
            updated_portfolio = dash_app.portfolio_service.add_ticker(store_data, selected_ticker, 1)
            logger.info(f"Ticker {selected_ticker} adicionado")
            return orjson_dumps(updated_portfolio).decode('utf-8'), None, "", False, False
        except ValueError as e:
            logger.error(f"Erro ao adicionar ticker: {e}")
            return no_update, None, str(e), True, current_tickers + 1 >= tickers_limit