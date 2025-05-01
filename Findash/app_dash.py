from dash import Dash, html, dcc, Output, Input, State, callback
from dash import dash_table
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from Findash.modules.metrics import calcular_metricas
from datetime import datetime, timedelta
import pandas as pd
from Findash.services.portfolio_services import PortfolioService
from Findash.utils.serialization import orjson_dumps, orjson_loads
import flask

def init_dash(flask_app, portfolio_service):
    dash_app = Dash(
        __name__, 
        server=flask_app, 
        url_base_pathname='/dash/',
        external_stylesheets=[dbc.themes.FLATLY]
        )
    dash_app.portfolio_service = portfolio_service
    
    # Configurar o Flask subjacente para usar orjson em respostas JSON
    # Mantido: Garante que os callbacks do Dash usem orjson para serializar respostas
    def orjson_response(data):
        return flask_app.response_class(
            response=orjson_dumps(data),
            mimetype='application/json'
        )
    flask_app.json_encoder = orjson_dumps
    flask_app.json_decoder = orjson_loads
    dash_app.server.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    # Lista estática de tickers
    TICKERS = [
        {"symbol": "PETR4.SA", "name": "Petrobras PN"},
        {"symbol": "VALE3.SA", "name": "Vale ON"},
        {"symbol": "ITUB4.SA", "name": "Itaú Unibanco PN"},
        {"symbol": "BBDC4.SA", "name": "Bradesco PN"},
        {"symbol": "ABEV3.SA", "name": "Ambev ON"},
    ]
    ticker_options = [{'label': f"{t['symbol']} - {t['name']}", 'value': t['symbol']} for t in TICKERS]

    # Layout
    dash_app.layout = html.Div([
        # ALTERAÇÃO: Removido storage_options do dcc.Store
        # Motivo: A versão do Dash (3.0.4) não suporta storage_options, causando TypeError
        # Impacto: dcc.Store usará json padrão internamente; serialização com orjson será feita manualmente nos callbacks
        dcc.Store(id='data-store', storage_type='session', data=None),
        html.H1("Dashboard de Portfólio", className="mb-4"),
        dbc.Row([
            # Coluna Esquerda (1/3)
            dbc.Col([
                html.Div([
                    dbc.Select(
                        id='ticker-dropdown',
                        options=ticker_options,
                        value=None,
                        placeholder="Selecione um ticker",
                        className="form-select me-2",
                        size="sm",
                        style={'width': '80%', 'fontSize': '12px'}
                    ),
                    dcc.Input(
                        id='start-date-input',
                        type='date',
                        value=None,
                        className="form-control me-2",
                        style={'width': '25%', 'fontSize': '12px', 'minWidth': '130px', 'height': '31px'}
                    ),
                    dcc.Input(
                        id='end-date-input',
                        type='date',
                        value=None,
                        className="form-control",
                        style={'width': '25%', 'fontSize': '12px', 'minWidth': '130px', 'height': '31px'}
                    ),
                    html.Button(
                        'Atualizar Período',
                        id='update-period-button',
                        n_clicks=0,
                        className="btn btn-primary btn-sm mt-2"
                    ),
                ], className="d-flex flex-wrap align-items-center mb-2"),
                dash_table.DataTable(
                    id='price-table',
                    columns=[
                        {'name': '', 'id': 'acao', 'editable': False},
                        {'name': 'Ticker', 'id': 'ticker', 'editable': False},
                        {'name': 'Total(%)', 'id': 'retorno_total', 'editable': False},
                        {'name': 'Quant.', 'id': 'quantidade', 'editable': True, 'type': 'numeric'},
                        {'name': 'Peso(%)', 'id': 'peso_quantidade_percentual', 'editable': False},
                        {'name': 'GCAP', 'id': 'ganho_capital', 'editable': False},
                        {'name': 'DY', 'id': 'proventos', 'editable': False},
                    ],
                    data=[],
                    style_table={'overflowX': 'auto', 
                                 'marginTop': '20px', 
                                 'height': '200px',
                                 'border': '1px solid #dee2e6',
                                 'overflowY': 'auto'
                                 },
                    fixed_rows={'headers': True},  
                    style_cell={
                        'fontSize': '12px', 'textAlign': 'center', 'minWidth': '50px',
                        'backgroundColor': '#f8f9fa', 'borderBottom': '1px solid #dee2e6', 'padding': '3px'
                    },
                    style_header={'fontWeight': 'bold', 
                                  'backgroundColor': '#f8f9fa', 
                                  'borderBottom': '2px solid #dee2e6',
                                  'position': 'sticky',
                                  'top': 0,
                                  'zIndex': 1
                                  },
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f2f2f2'},
                        {'if': {'filter_query': '{ticker} = "Total"'}, 
                         'fontWeight': 'bold', 
                         'backgroundColor': '#e9ecef',
                         'position': 'sticky',
                         'bottom': 0,
                         'zIndex': 1
                         },
                        {'if': {'column_id': 'acao'}, 'cursor': 'pointer', 'color': '#007bff'},
                        {'if': {'column_id': 'acao', 'state': 'active'}, 'color': '#dc3545'},
                    ],
                    editable=True
                ),
                dcc.Graph(id='portfolio-treemap', style={'width': '100%', 'height': '200px', 'marginTop': '10px'}),
                dcc.Graph(id='financial-treemap', style={'width': '100%', 'height': '200px', 'marginTop': '10px'})
            ], md=4, className="p-1", style={
                'backgroundColor': '#f5f5f5', 
                'maxHeight': '750px',
                'overflow': 'hidden',
                'border': '1px solid red'
                }),
            # Coluna Direita (2/3)
            dbc.Col([
                html.Div("Cards com Indicadores (Placeholder)", className="mb-3"),
                dcc.Graph(id='portfolio-ibov-line', style={'width': '100%', 'height': '200px'}),
                dcc.Graph(id='individual-tickers-line', style={'width': '100%', 'height': '200px', 'marginTop': '10px'}),
                dcc.Graph(id='stacked-area-chart', style={'width': '100%', 'height': '200px', 'marginTop': '10px'})
            ], md=8, className="p-1", style={
                'border': '1px solid blue'
            }),
        ], className="mb-3", align="start", style={
            'flexWrap': 'nowrap'
            }),
        # Linha de largura total para os três novos elementos
        dbc.Row([
            # Coluna para o Gráfico 1 (Capital Gains e Dividend Yield)
            dbc.Col([
                dcc.Graph(id='capital-dividend-chart', style={'width': '100%', 'height': '200px'})
            ], md=4, className="p-2"),
            # Placeholder para o Gráfico 2 (Dividendos por Setor)
            dbc.Col([
                dcc.Graph(id='dividend-by-sector-chart', style={'width': '100%', 'height': '200px'})
            ], md=4, className="p-2"),
            # Placeholder para a Tabela (Ranking de DY)
            dbc.Col([
                dcc.Graph(id='cumulative-gains-dividends-chart', style={'width': '100%', 'height': '200px'})
            ], md=4, className="p-2"),
        ], className="g-3"),
        # Três Colunas Inferiores
        dbc.Row([
            dbc.Col([
                dcc.Graph(id='sector-donut-charts', style={'width': '100%', 'height': '300px'})
            ], md=4, className="p-2"),
            dbc.Col([
                dcc.Graph(id='correlation-heatmap', style={'width': '100%', 'height': '300px'})
            ], md=4, className="p-2"),
            dbc.Col([
                dcc.Graph(id='volatility-chart', style={'width': '100%', 'height': '300px'})
            ], md=4, className="p-2"),
        ], className="g-3"),
    ], className="p-4 container-fluid")

    # Callbacks
    @dash_app.callback(
        [Output('price-table', 'data'),
         Output('data-store', 'data')],
        [Input('data-store', 'data'),
         Input('price-table', 'data')],
        State('price-table', 'data_previous'),
        prevent_initial_call=False
    )
    def update_price_table(store_data, table_data, table_data_previous):
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store são recebidos como string/bytes (serializados com json); convertemos para dict usando orjson
        # Impacto: Permite manipular dados complexos (ex.: datetime, numpy) sem depender de storage_options
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'portfolio' not in store_data or not store_data['portfolio']:
            print("Nenhum dado no store - Inicializando store_data")
            initial_data = {
                'tickers': [], 
                'quantities': [], 
                'portfolio': {}, 
                'ibov': {},
                'start_date': None, 
                'end_date': None, 
                'portfolio_values': {},
                'portfolio_return': {}, 
                'individual_returns': {}, 
                'ibov_return': {},
                'table_data': [], 
                'dividends': {ticker['symbol']: {} for ticker in TICKERS},
                'setor_pesos': {}, 
                'setor_pesos_financeiros': {},
                'individual_daily_returns': {},
                'portfolio_daily_return': {}
            }
            # ALTERAÇÃO: Serializar initial_data com orjson_dumps antes de salvar no dcc.Store
            # Motivo: Substitui serialização padrão (json) por orjson para maior performance
            # Impacto: Dados salvos são compatíveis com orjson_loads nos outros callbacks
            return [], orjson_dumps(initial_data).decode('utf-8')
        
        tickers = store_data['tickers']
        quantities = store_data['quantities']
        portfolio = store_data['portfolio']
        ibov = store_data.get('ibov', {})
        start_date = store_data['start_date']  
        end_date = store_data['end_date']
        dividends = store_data.get('dividends', {})

        if table_data is None or (table_data_previous is None and 'table_data' in store_data):
            print("Carga inicial: Usando table_data do store")
            table_data = store_data['table_data']
            # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
            # Motivo: Mantém consistência com a serialização manual
            return table_data, orjson_dumps(store_data).decode('utf-8')

        new_quantities = quantities.copy()
        if table_data and table_data != table_data_previous:
            print("Quantidades alteradas, recalculando métricas")
            table_quantities = {row['ticker']: int(row['quantidade']) for row in table_data if row['ticker'] != 'Total'}
            new_quantities = [table_quantities.get(ticker, quantities[i] if i < len(quantities) else 1) 
                            for i, ticker in enumerate(tickers)]

            result = calcular_metricas(portfolio, tickers, new_quantities, start_date, end_date, ibov, dividends=dividends)
            metrics = result['table_data']
        else:
            print("Nenhuma mudança nas quantidades, usando table_data do store")
            metrics = store_data['table_data']        

        ticker_quantities = dict(zip(tickers, new_quantities))
        updated_table_data = [row for row in metrics if row['ticker'] in tickers or row['ticker'] == 'Total']
        total_quantity = sum(ticker_quantities.values()) or 1
        for row in updated_table_data:
            if row['ticker'] != 'Total':
                row['quantidade'] = ticker_quantities.get(row['ticker'], 0)
                row['peso_quantidade_percentual'] = f"{(row['quantidade'] / total_quantity) * 100:.2f}%"
                row['acao'] = 'x'
            else:
                row['acao'] = "Total"
                row['quantidade'] = total_quantity
                row['peso_quantidade_percentual'] = "100.00%"

        updated_store_data = store_data.copy()
        updated_store_data['quantities'] = new_quantities
        if table_data and table_data != table_data_previous:
            updated_store_data.update(result)
        print(f"Store atualizado com quantidades {new_quantities}")

        # ALTERAÇÃO: Serializar updated_store_data com orjson_dumps antes de salvar no dcc.Store
        # Motivo: Garante que os dados salvos usem orjson, mantendo performance e compatibilidade
        return updated_table_data, orjson_dumps(updated_store_data).decode('utf-8')

    @dash_app.callback(
        Output('portfolio-treemap', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_portfolio_treemap(store_data):
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar os dados corretamente para gerar o treemap
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'table_data' not in store_data:
            print("Nenhum dado para o treemap de quantidade")
            return go.Figure(go.Treemap())

        table_data = store_data['table_data']
        treemap_data = [row for row in table_data if row['ticker'] != 'Total']
        treemap_fig = go.Figure(go.Treemap(
            labels=[row['ticker'] for row in treemap_data],
            parents=[""] * len(treemap_data),
            values=[float(row['peso_quantidade_percentual'].replace('%', '')) for row in treemap_data],
            text=[row['ticker'] for row in treemap_data],
            textinfo="text"
        ))
        treemap_fig.update_traces(hoverinfo="label+value")
        treemap_fig.update_layout(margin=dict(t=30, l=0, r=0, b=0), title="Peso por Quantidade")
        return treemap_fig   

    @dash_app.callback(
        Output('financial-treemap', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_financial_treemap(store_data):
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar os dados financeiros para gerar o treemap
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data
            
        if not store_data or 'tickers' not in store_data or 'quantities' not in store_data or 'portfolio_values' not in store_data:
            print("Nenhum dado para o treemap financeiro")
            return go.Figure()

        tickers = store_data['tickers']
        quantities = store_data['quantities']
        portfolio_values = store_data['portfolio_values']

        valores_financeiros = []
        for ticker, quantidade in zip(tickers, quantities):
            if ticker in portfolio_values and portfolio_values[ticker]:
                ultimo_valor = list(portfolio_values[ticker].values())[-1]
                valor_financeiro = quantidade * ultimo_valor
                valores_financeiros.append(valor_financeiro)
            else:
                valores_financeiros.append(0.0)

        total_financeiro = sum(valores_financeiros)
        if total_financeiro > 0:
            pesos_financeiros = [v / total_financeiro * 100 for v in valores_financeiros]
            fig = go.Figure(go.Treemap(
                labels=tickers,
                parents=[""] * len(tickers),
                values=pesos_financeiros,
                text=[f"{p:.2f}%" for p in pesos_financeiros],
                textinfo="label+text"
            ))
            fig.update_layout(margin=dict(t=30, l=0, r=0, b=0), title="Peso Financeiro")
            return fig
        return go.Figure()

    @dash_app.callback(
        Output('portfolio-ibov-line', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_portfolio_ibov_line(store_data):
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar portfolio_return e ibov_return para gerar o gráfico
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'portfolio_return' not in store_data or 'ibov_return' not in store_data:
            print("Nenhum dado no store para o gráfico")
            return go.Figure()

        portfolio_return = store_data['portfolio_return']
        ibov_return = store_data['ibov_return']

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(portfolio_return.keys()),
            y=list(portfolio_return.values()),
            mode='lines',
            name='Portfólio',
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=list(ibov_return.keys()),
            y=list(ibov_return.values()),
            mode='lines',
            name='IBOV',
            line=dict(color='orange')
        ))
        fig.update_layout(
            title='Retorno Acumulado: Portfólio vs IBOV',
            yaxis_title='Retorno Acumulado (%)',
            legend=dict(x=0, y=1),
            margin=dict(l=50, r=50, t=50, b=50)
        )
        print("Gráfico portfolio-ibov-line gerado com métricas do store")
        return fig

    @dash_app.callback(
        Output('data-store', 'data', allow_duplicate=True),
        Input('price-table', 'active_cell'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def delete_ticker(active_cell, store_data):
        """
        Remove um ticker do portfólio usando o PortfolioService.
        """
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar tickers e outros dados para remoção
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not active_cell or not store_data or not store_data['tickers']:
            # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
            # Motivo: Mantém consistência com a serialização manual
            return orjson_dumps(store_data).decode('utf-8') if store_data else None
        
        row = active_cell['row']
        col = active_cell['column_id']
        
        if col == 'acao' and row < len(store_data['tickers']):
            ticker_to_remove = store_data['tickers'][row]
            try:
                updated_portfolio = dash_app.portfolio_service.remove_ticker(store_data, ticker_to_remove)
                print(f"Ticker {ticker_to_remove} removido com sucesso")
                # ALTERAÇÃO: Serializar updated_portfolio com orjson_dumps antes de salvar
                # Motivo: Garante que os dados salvos usem orjson
                return orjson_dumps(updated_portfolio).decode('utf-8')
            except ValueError as e:
                print(f"Erro ao remover ticker: {e}")
                # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
                # Motivo: Mantém consistência com a serialização manual
                return orjson_dumps(store_data).decode('utf-8')
        
        # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
        # Motivo: Mantém consistência com a serialização manual
        return orjson_dumps(store_data).decode('utf-8')

    @dash_app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('ticker-dropdown', 'value')],
        Input('ticker-dropdown', 'value'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def add_ticker(selected_ticker, store_data):
        """
        Adiciona um ticker ao portfólio usando o PortfolioService.
        """
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar dados para adicionar ticker
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not selected_ticker or not store_data:
            # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
            # Motivo: Mantém consistência com a serialização manual
            return orjson_dumps(store_data).decode('utf-8') if store_data else None, None
        
        try:
            updated_portfolio = dash_app.portfolio_service.add_ticker(store_data, selected_ticker, 1)
            # ALTERAÇÃO: Serializar updated_portfolio com orjson_dumps antes de salvar
            # Motivo: Garante que os dados salvos usem orjson
            return orjson_dumps(updated_portfolio).decode('utf-8'), None
        except ValueError as e:
            print(f"Erro ao adicionar ticker: {e}")
            # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
            # Motivo: Mantém consistência com a serialização manual
            return orjson_dumps(store_data).decode('utf-8'), None

    @dash_app.callback(
        Output('data-store', 'data', allow_duplicate=True),
        Input('update-period-button', 'n_clicks'),
        State('start-date-input', 'value'),
        State('end-date-input', 'value'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def update_period(n_clicks, start_date, end_date, store_data):
        """
        Atualiza o período do portfólio usando o PortfolioService.
        """
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar dados para atualizar período
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not n_clicks or not start_date or not end_date or not store_data:
            # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
            # Motivo: Mantém consistência com a serialização manual
            return orjson_dumps(store_data).decode('utf-8') if store_data else None

        try:
            updated_portfolio = dash_app.portfolio_service.update_portfolio_period(store_data, start_date, end_date)
            print(f"Período atualizado: {start_date} a {end_date}")
            # ALTERAÇÃO: Serializar updated_portfolio com orjson_dumps antes de salvar
            # Motivo: Garante que os dados salvos usem orjson
            return orjson_dumps(updated_portfolio).decode('utf-8')
        except ValueError as e:
            print(f"Erro ao atualizar período: {e}")
            # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
            # Motivo: Mantém consistência com a serialização manual
            return orjson_dumps(store_data).decode('utf-8')
    
    @dash_app.callback(
        Output('individual-tickers-line', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_individual_tickers_line(store_data):
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar individual_returns para gerar o gráfico
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'individual_returns' not in store_data:
            print("Nenhum dado no store para o gráfico de tickers individuais")
            return go.Figure()

        individual_returns = store_data['individual_returns']
        tickers = store_data['tickers']

        fig = go.Figure()
        colors = ['blue', 'green', 'red', 'purple', 'orange']
        for i, ticker in enumerate(tickers):
            if ticker in individual_returns:
                fig.add_trace(go.Scatter(
                    x=list(individual_returns[ticker].keys()),
                    y=list(individual_returns[ticker].values()),
                    mode='lines',
                    name=ticker,
                    line=dict(color=colors[i % len(colors)])
                ))

        fig.update_layout(
            title='Retorno Acumulado: Tickers Individuais',
            yaxis_title='Retorno Acumulado (%)',
            legend=dict(x=0, y=1),
            margin=dict(l=50, r=50, t=50, b=50)
        )
        print(f"Gráfico de tickers individuais gerado para: {tickers}")
        return fig
    
    @dash_app.callback(
        Output('stacked-area-chart', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_stacked_area_chart(store_data):
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar portfolio_values para gerar o gráfico
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'portfolio_values' not in store_data:
            print("Nenhum dado no store para o gráfico de área empilhada")
            return go.Figure()

        portfolio_values = pd.DataFrame(store_data['portfolio_values'])
        tickers = store_data['tickers']

        fig = go.Figure()
        colors = ['blue', 'green', 'red', 'purple', 'orange']
        for i, ticker in enumerate(tickers):
            if ticker in portfolio_values.columns:
                fig.add_trace(go.Scatter(
                    x=portfolio_values.index,
                    y=portfolio_values[ticker],
                    mode='lines',
                    name=ticker,
                    stackgroup='one',
                    line=dict(width=0),
                    fillcolor=colors[i % len(colors)],
                    opacity=0.7
                ))

        fig.update_layout(
            title='Composição do Portfólio: Área Empilhada',
            yaxis_title='Valor do Portfólio (R$)',
            legend=dict(x=0, y=1),
            margin=dict(l=50, r=50, t=50, b=50),
            showlegend=True
        )
        print(f"Gráfico de área empilhada gerado para: {tickers}")
        return fig
       
    @dash_app.callback(
        Output('capital-dividend-chart', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_capital_dividend_chart(store_data):
        """
        Gera um gráfico de colunas lado a lado com ganho de capital, dividend yield e retorno total.
        """
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar portfolio_values, dividends, etc. para gerar o gráfico
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'portfolio_values' not in store_data or 'tickers' not in store_data:
            print("Nenhum dado para o gráfico de ganho de capital e dividend yield")
            return go.Figure()

        tickers = store_data['tickers']
        quantities = store_data['quantities']
        portfolio_values = store_data['portfolio_values']
        dividends = store_data.get('dividends', {})
        start_date = store_data['start_date']
        end_date = store_data['end_date']

        if not start_date or not end_date or not tickers:
            print("Dados incompletos (start_date, end_date ou tickers)")
            return go.Figure()

        metrics = dash_app.portfolio_service.calcular_metricas_mensais_anuais(tickers, quantities, portfolio_values, dividends, start_date, end_date)

        periods = metrics['periods']
        capital_gains = metrics['capital_gains']
        dividend_yields = metrics['dividend_yields']
        total_returns = metrics['total_returns']

        print(f"Valores calculados para o gráfico:")
        print(f"Períodos: {periods}")
        print(f"Ganho de Capital (%): {capital_gains}")
        print(f"Dividend Yield (%): {dividend_yields}")
        print(f"Retorno Total (%): {total_returns}")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=periods,
            y=capital_gains,
            name='Ganho de Capital',
            marker_color='#F5CBA7',
            text=[f"{y:.1f}%" for y in capital_gains],
            textposition='auto'
        ))
        fig.add_trace(go.Bar(
            x=periods,
            y=dividend_yields,
            name='Dividend Yield',
            marker_color='#D35400',
            text=[f"{y:.1f}%" for y in dividend_yields if y > 0],
            textposition='auto'
        ))
        fig.add_trace(go.Scatter(
            x=periods,
            y=total_returns,
            mode='markers',
            name='Retorno Total',
            marker=dict(
                size=6,
                color='black',
                symbol='circle',
                line=dict(width=1, color='white')
            ),
            text=[f"{y:.1f}%" for y in total_returns],
            hoverinfo='text'
        ))
        fig.update_layout(
            title='Ganho de Capital e Dividend Yield',
            yaxis_title='Retorno (%)',
            barmode='group',
            bargap=0.3,
            height=200,
            margin=dict(l=40, r=40, t=60, b=40),
            legend=dict(
                x=0.5,
                y=1.1,
                xanchor='center',
                yanchor='bottom',
                bgcolor='rgba(255,255,255,0.5)',
                orientation='h'
            ),
            yaxis=dict(
                tickformat='.1f',
                ticksuffix='%',
                autorange=True
            )
        )
        print(f"Gráfico de ganho de capital e dividend yield gerado para {len(periods)} períodos")
        return fig
    
    @dash_app.callback(
        Output('dividend-by-sector-chart', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_dividend_by_sector_chart(store_data):
        """
        Gera um gráfico de barras com o Dividend Yield por setor.
        """
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar portfolio_values, dividends, etc. para gerar o gráfico
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        print("Callback update_dividend_by_sector_chart acionado")
        if not store_data or 'portfolio_values' not in store_data or 'tickers' not in store_data:
            print("Nenhum dado para o gráfico de dividendos por setor")
            return go.Figure()

        tickers = store_data['tickers']
        quantities = store_data['quantities']
        portfolio_values = store_data['portfolio_values']
        dividends = store_data.get('dividends', {})
        start_date = store_data['start_date']
        end_date = store_data['end_date']

        print(f"Dados recebidos no callback - Tickers: {tickers}")
        print(f"Quantities: {quantities}")
        print(f"Start Date: {start_date}, End Date: {end_date}")
        print(f"Dividend Keys: {list(dividends.keys())}")

        if not start_date or not end_date or not tickers:
            print("Dados incompletos (start_date, end_date ou tickers)")
            return go.Figure()

        metrics = dash_app.portfolio_service.calcular_dy_por_setor(tickers, quantities, portfolio_values, dividends, start_date, end_date)

        years = metrics['years']
        setores = metrics['setores']
        dy_por_setor_por_ano = metrics['dy_por_setor_por_ano']

        print(f"Valores calculados para o gráfico de dividendos por setor:")
        print(f"Anos: {years}")
        print(f"Setores: {setores}")
        print(f"DY por setor por ano: {dy_por_setor_por_ano}")

        fig = go.Figure()
        colors = ['#FF9999', '#FF6666', '#FF3333']
        for idx, year in enumerate(years):
            dy_values = [dy_por_setor_por_ano[setor][year] for setor in setores]
            print(f"DY values para {year}: {dy_values}")
            fig.add_trace(go.Bar(
                x=setores,
                y=dy_values,
                name=year,
                marker_color=colors[idx % len(colors)],
                text=[f"{y:.1f}%" for y in dy_values if y > 0],
                textposition='auto'
            ))

        fig.update_layout(
            title='Dividend Yield por Setor',
            yaxis_title='Dividend Yield (%)',
            barmode='group',
            bargap=0.3,
            bargroupgap=0.0,
            height=200,
            margin=dict(l=40, r=40, t=60, b=40),
            legend=dict(
                x=0.5,
                y=1.1,
                xanchor='center',
                yanchor='bottom',
                bgcolor='rgba(255,255,255,0.5)',
                orientation='h'
            ),
            yaxis=dict(
                tickformat='.1f',
                ticksuffix='%',
                autorange=True
            ),
            annotations=[
                dict(
                    x=1,
                    y=-0.2,
                    xref="paper",
                    yref="paper",
                    text="* Anos incompletos foram anualizados",
                    showarrow=False,
                    font=dict(size=10)
                )
            ]
        )
        print(f"Gráfico de dividendos por setor gerado para {len(setores)} setores e {len(years)} anos")
        return fig
    
    @dash_app.callback(
        Output('cumulative-gains-dividends-chart', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_cumulative_gains_dividends_chart(store_data):
        """
        Gera um gráfico de linhas mostrando o retorno total acumulado e o DY acumulado.
        """
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar portfolio_values, dividends, etc. para gerar o gráfico
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        print("Callback update_cumulative_gains_dividends_chart acionado")
        if not store_data or 'tickers' not in store_data or 'portfolio_values' not in store_data:
            print("Nenhum dado válido no store para o gráfico de linhas")
            return go.Figure().update_layout(
                title="Retorno Total e DY Acumulados (%)",
                annotations=[dict(text="Sem dados", x=0.5, y=0.5, showarrow=False)]
            )

        tickers = store_data.get('tickers', [])
        quantities = store_data.get('quantities', [1] * len(tickers))
        portfolio_values = store_data.get('portfolio_values', {})
        dividends = store_data.get('dividends', {})
        start_date = store_data.get('start_date', '2024-01-01')
        end_date = store_data.get('end_date', '2025-04-23')

        print(f"Dados recebidos no callback - Tickers: {tickers}, Start Date: {start_date}, End Date: {end_date}")

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        portfolio_df = pd.DataFrame()
        for ticker in tickers:
            if ticker in portfolio_values and portfolio_values[ticker]:
                df = pd.DataFrame.from_dict(portfolio_values[ticker], orient='index', columns=[ticker])
                df.index = pd.to_datetime(df.index)
                portfolio_df = portfolio_df.join(df, how='outer') if not portfolio_df.empty else df
        portfolio_df = portfolio_df.ffill().loc[start:end]

        if portfolio_df.empty:
            print("DataFrame de preços vazio para o período")
            return go.Figure().update_layout(
                title="Retorno Total e DY Acumulados (%)",
                annotations=[dict(text="Sem dados", x=0.5, y=0.5, showarrow=False)]
            )

        total_portfolio = pd.DataFrame()
        for ticker, qty in zip(tickers, quantities):
            if ticker in portfolio_df.columns:
                total_portfolio[ticker] = portfolio_df[ticker] * qty
        portfolio_series = total_portfolio.sum(axis=1)

        initial_value = portfolio_series.iloc[0]
        if initial_value == 0:
            print("Valor inicial do portfólio é zero, não é possível calcular percentuais")
            return go.Figure().update_layout(
                title="Retorno Total e DY Acumulados (%)",
                annotations=[dict(text="Valor inicial zero", x=0.5, y=0.5, showarrow=False)]
            )

        gains_series = ((portfolio_series - initial_value) / initial_value) * 100

        dividend_dates = []
        dividend_totals = []
        cumulative_dividends = 0
        all_dates = pd.date_range(start=start, end=end, freq='D')
        
        for date in all_dates:
            date_str = date.strftime('%Y-%m-%d')
            daily_dividend = 0
            for ticker, qty in zip(tickers, quantities):
                if ticker in dividends and date_str in dividends[ticker]:
                    daily_dividend += dividends[ticker][date_str] * qty
            cumulative_dividends += daily_dividend
            dividend_dates.append(date)
            dividend_totals.append(cumulative_dividends)

        dividend_series = pd.Series(dividend_totals, index=dividend_dates)
        dividend_series = dividend_series.reindex(portfolio_series.index, method='ffill').fillna(0)
        dy_series = (dividend_series / initial_value) * 100

        total_return = gains_series + dy_series

        print(f"DY acumulado (%) (amostra): {dy_series.tail().to_dict()}")
        print(f"Retorno total acumulado (%) (amostra): {total_return.tail().to_dict()}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=total_return.index,
            y=total_return.values,
            mode='lines',
            name='Retorno Total Acumulado (%)',
            line=dict(color='blue'),
            hovertemplate='%{x|%Y-%m-%d}: %{y:.2f}%'
        ))
        fig.add_trace(go.Scatter(
            x=dy_series.index,
            y=dy_series.values,
            mode='lines',
            name='DY Acumulado (%)',
            line=dict(color='green'),
            hovertemplate='%{x|%Y-%m-%d}: %{y:.2f}%'
        ))
        fig.update_layout(
            title="Retorno Total e DY Acumulados (%)",
            xaxis_title="Data",
            yaxis_title="Retorno Acumulado (%)",
            margin=dict(l=20, r=20, t=40, b=20),
            height=200,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        print(f"Gráfico de linhas gerado com {len(total_return)} pontos de dados")
        return fig
        
    @dash_app.callback(
        Output('sector-donut-charts', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_sector_bar_chart(store_data):
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar setor_pesos e setor_pesos_financeiros para gerar o gráfico
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'setor_pesos' not in store_data or 'setor_pesos_financeiros' not in store_data:
            print("Nenhum dado para o gráfico de setores")
            return go.Figure()

        setor_pesos = store_data['setor_pesos']
        setor_pesos_financeiros = store_data['setor_pesos_financeiros']
        
        setor_abreviado = {
            "Petróleo, Gás e Biocombustíveis": "Petróleo\ne Gás",
            "Materiais Básicos": "Materiais\nBásicos",
            "Bens Industriais": "Bens\nIndustriais",
            "Consumo Não Cíclico": "Consumo\nNão Cíclico",
            "Consumo Cíclico": "Consumo\nCíclico",
            "Saúde": "Saúde",
            "Tecnologia e Comunicação": "Tech e\nComunicação",
            "Utilidade Pública": "Utilidade\nPública",
            "Financeiro e Outros": "Financeiro\ne Outros"
        }
        
        setores_completos = [s for s in setor_pesos.keys() if setor_pesos[s] > 0 or setor_pesos_financeiros[s] > 0]
        setores = [setor_abreviado[s] for s in setores_completos]
        pesos_quantidade = [setor_pesos[s] for s in setores_completos]
        pesos_financeiros = [setor_pesos_financeiros[s] for s in setores_completos]

        fig = go.Figure(data=[
            go.Bar(
                x=setores,
                y=pesos_quantidade,
                name='Peso por Quantidade',
                marker_color='#1f77b4',
                text=[f"{p:.1f}%" for p in pesos_quantidade],
                textposition='auto'
            ),
            go.Bar(
                x=setores,
                y=pesos_financeiros,
                name='Peso Financeiro',
                marker_color='#ff7f0e',
                text=[f"{p:.1f}%" for p in pesos_financeiros],
                textposition='auto'
            )
        ])
        fig.update_layout(
            title="Pesos por Setor",
            yaxis_title="Percentual (%)",
            barmode='group',
            bargap=0.15,
            bargroupgap=0.1,
            height=300,
            margin=dict(l=40, r=80, t=60, b=40),
            legend=dict(
                x=0.5,
                y=1.1,
                xanchor='center',
                yanchor='bottom',
                bgcolor='rgba(255,255,255,0.5)',
                orientation='h'
            )
        )
        return fig

    @dash_app.callback(
        Output('correlation-heatmap', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_correlation_heatmap(store_data):
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar individual_returns para gerar o heatmap
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'individual_returns' not in store_data or not store_data['individual_returns']:
            print("Nenhum dado para o gráfico de correlação")
            return go.Figure()

        individual_returns = store_data['individual_returns']
        tickers = store_data['tickers']
        returns_df = pd.DataFrame({ticker: individual_returns.get(ticker, {}) for ticker in tickers})
        returns_df = returns_df.apply(pd.to_numeric, errors='coerce').dropna()

        if returns_df.empty or len(returns_df.columns) < 2:
            print("Dados insuficientes para calcular correlação")
            return go.Figure()
        correlation_matrix = returns_df.corr()

        fig = go.Figure(data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.index,
            colorscale='RdBu',
            zmin=-1, zmax=1,
            text=[[f"{val:.2f}" for val in row] for row in correlation_matrix.values],
            hoverinfo='text',
            colorbar=dict(title="Correlação")
        ))
        fig.update_layout(
            title="Correlação entre Tickers",
            xaxis_title="Tickers",
            yaxis_title="Tickers",
            margin=dict(l=40, r=40, t=60, b=40),
            height=300
        )
        return fig

    @dash_app.callback(
        Output('volatility-chart', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    def update_volatility_chart(store_data):
        # ALTERAÇÃO: Desserializar store_data com orjson_loads
        # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
        # Impacto: Permite acessar individual_daily_returns e portfolio_daily_return para gerar o gráfico
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'individual_daily_returns' not in store_data or 'portfolio_daily_return' not in store_data:
            print("Nenhum dado para o gráfico de volatilidade")
            return go.Figure()

        individual_daily_returns = store_data['individual_daily_returns']
        portfolio_daily_return = store_data['portfolio_daily_return']
        tickers = store_data['tickers']
        
        returns_df = pd.DataFrame({ticker: individual_daily_returns.get(ticker, {}) for ticker in tickers})
        returns_df = returns_df.apply(pd.to_numeric, errors='coerce').dropna()
        returns_df['Portfolio'] = pd.Series(portfolio_daily_return).reindex(returns_df.index).fillna(0)

        print("Retornos diários (amostra):")
        print(returns_df.head())
        
        volatilities = returns_df.std() * (252 ** 0.5)
        print("Volatilities anualizadas (%):")
        print(volatilities)

        fig = go.Figure(go.Bar(
            x=volatilities.index,
            y=volatilities.values,
            text=[f"{v:.2f}%" for v in volatilities.values],
            textposition='auto',
            marker_color=['#1f77b4'] * len(tickers) + ['#ff7f0e'],
        ))
        fig.update_layout(
            title="Volatilidade Anualizada",
            yaxis_title="Volatilidade (%)",
            xaxis_title="Tickers",
            margin=dict(l=40, r=40, t=60, b=40),
            height=300,
            bargap=0.2
        )
        return fig

    return dash_app