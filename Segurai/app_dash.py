import dash
from dash import html, dcc, Input, Output
import flask
import json

def init_segurai_dash(server):
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname='/dash/segurai/',
        suppress_callback_exceptions=True
    )
    # Função para construir o layout dinamicamente (acessa flask.session com segurança)
    def serve_layout():
        segurai_data = flask.session.get("segurai_data")
        if isinstance(segurai_data, str):
            segurai_data = json.loads(segurai_data)

        return html.Div([
            dcc.Store(id='store-segurai-data', data=segurai_data),
            html.Div(id='resultado-score')
        ])

    # Atribui a função dinâmica ao layout
    app.layout = serve_layout

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
