import dash
from dash import html, dcc, Input, Output, State
import flask
from utils.serialization import orjson_dumps, orjson_loads

# Função para construir o layout dinamicamente (acessa flask.session com segurança)
def serve_layout():
    resultado = flask.session.get("segurai_resultado")
    print("Dados recebidos na sessão:", resultado)

    if isinstance(resultado, str):
        resultado = orjson_loads(resultado)

    return html.Div([
        dcc.Store(id='store-segurai-resultado', data=resultado),
        html.Div(id='resultado-score')
    ])

def init_segurai_dash(server):
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname='/dash/segurai/',
        suppress_callback_exceptions=True
    )
    
    # Atribui a função dinâmica ao layout
    app.layout = serve_layout

    @app.callback(
        Output('resultado-score', 'children'),
        Input('store-segurai-resultado', 'data')
    )
    def mostrar_resultado(data):
        print("Callback ativado com data:", data)

        if not data:
            return html.P("Nenhum dado disponível.")

        if isinstance(data, str):  # deserializar se vier como JSON
            data = orjson_loads(data)
        
        entrada = data.get('entrada', {})
        resultados = data.get('resultado', [])

        return html.Div([
            html.H2("Informações do Usuário"),
            html.Ul([
                html.Li(f"Idade: {entrada.get('idade')}"),
                html.Li(f"Renda: R$ {entrada.get('renda')}"),
                html.Li(f"Sinistro Anterior: {'Sim' if entrada.get('sinistro') else 'Não'}"),
                html.Li(f"UF: {entrada.get('uf')}"),
                html.Li(f"Tipo de Seguro: {entrada.get('tipo_seguro')}"),
                html.Li(f"Estado Civil: {entrada.get('estado_civil')}")
            ]),
            html.Hr(),
            html.H2("Resultado da Análise de Risco"),
            html.Table([
                html.Thead([
                    html.Tr([html.Th("Modelo"), html.Th("Classificação"), html.Th("Score")])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(res['modelo']),
                        html.Td(res['classe']),
                        html.Td(f"{res['score']:.2f}")
                    ]) for res in resultados 
                ])
            ], style={'width': '50%', 'border': '1px solid #ccc', 'margin-top': '20px'})
        ])


    return app
