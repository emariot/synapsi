from dash import Dash, Output, Input
from utils.serialization import orjson_loads

def register_table_callbacks(dash_app: Dash):
    """
    Registra callbacks relacionados à tabela e inputs de dados no Dash app.
    
    Args:
        dash_app (Dash): Instância do aplicativo Dash.
    """
    @dash_app.callback(
        Output('date-input-range-picker', 'value'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def carregar_datas_iniciais(store_data):
        """
        Preenche os inputs de data com os valores do dcc.Store ao iniciar o app.
        """
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data
            start_date = store_data.get('start_date')
            end_date = store_data.get('end_date')
            if start_date and end_date:
                return [start_date, end_date]
        
        return None