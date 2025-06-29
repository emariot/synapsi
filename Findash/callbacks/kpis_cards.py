from dash import Dash, Output, Input
from utils.serialization import orjson_loads
from Findash.utils.formatting import format_kpi
from Findash.utils.logging_tools import log_callback


def register_kpis_card(dash_app: Dash):

    @dash_app.callback(
            [Output("kpi-sharpe-value", "children"),
            Output("kpi-sortino-value", "children"),
            Output("kpi-retorno-value", "children"),
            Output("kpi-volat-value", "children"),
            Output("kpi-drawdown-value", "children"),
            Output("kpi-alpha-value", "children"),
            Output("kpi-beta-value", "children")],
            Input('data-store', 'data'),
            prevent_initial_call=True
        )
    @log_callback("update_kpi_cards")
    def update_kpi_cards(store_data):
        """
        Atualiza os valores dos KpiCards quando o data-store muda.
        
        Args:
            store_data: Dados armazenados no dcc.Store, contendo os KPIs do portfólio.
        
        Returns:
            Lista de strings formatadas para os dmc.Text de cada KpiCard.
        """
        # Desserializar store_data
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data
        else:
            store_data = {}

        # Obter KPIs ou usar valores padrão
        kpis = store_data.get("kpis", {})

        return (
            format_kpi("sharpe", kpis.get("sharpe")),
            format_kpi("sortino", kpis.get("sortino")),
            format_kpi("retorno_medio_anual", kpis.get("retorno_medio_anual")),
            format_kpi("volatilidade", kpis.get("volatilidade")),
            format_kpi("max_drawdown", kpis.get("max_drawdown")),
            format_kpi("alpha", kpis.get("alpha")),
            format_kpi("beta", kpis.get("beta"))
        )