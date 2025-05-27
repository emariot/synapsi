import dash
from dash import html, dcc, Input, Output
import json

def init_segurai_dash(server):
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname='/dash/segurai/',
        suppress_callback_exceptions=True
    )

    app.layout = html.Div([
        dcc.Store(id='store-segurai-data'),  # será preenchido pela sessão
        html.Div(id='resultado-score')
    ])

    @app.callback(
        Output('resultado-score', 'children'),
        Input('store-segurai-data', 'data')
    )
    def mostrar_resultado(data):
        if not data:
            return html.P("Nenhum dado disponível.")

        if isinstance(data, str):  # deserializar se vier como JSON
            data = json.loads(data)

        return html.Div([
            html.H2("Resultado da Análise de Risco"),
            html.P(f"Idade: {data['idade']}"),
            html.P(f"Estado: {data['uf']}"),
            html.P(f"Tipo de Seguro: {data['tipo_seguro']}"),
            html.H4(f"Score de Risco: {data['score']}"),
            html.P(f"Classificação: {data['classificacao']}"),
        ])

    return app
