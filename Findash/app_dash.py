import dash
from dash import Dash, html, dcc, Output, Input, State, callback, no_update, dash_table
import plotly.graph_objects as go
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
from Findash.modules.metrics import calcular_metricas
from datetime import datetime, timedelta
import pandas as pd
from Findash.services.portfolio_services import PortfolioService
from utils.serialization import orjson_dumps, orjson_loads
from flask import session, has_request_context
import requests
import orjson

import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger('yfinance').setLevel(logging.WARNING)
logging.getLogger('sqlitedict').setLevel(logging.WARNING)

# Alteração: Configurar logger do Werkzeug para nível INFO
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)

# Alteração: Filtro personalizado para suprimir logs de requisições HTTP específicas do Dash
class DashRequestFilter(logging.Filter):
    def filter(self, record):
        # Ignora mensagens de requisições GET/POST para rotas do Dash
        if 'GET /dash' in record.msg or 'POST /dash' in record.msg:
            return False
        return True

werkzeug_logger.addFilter(DashRequestFilter())

# Lista estática de tickers
TICKERS = [
    {"symbol": "PETR4.SA", "name": "Petrobras PN"},
    {"symbol": "VALE3.SA", "name": "Vale ON"},
    {"symbol": "ITUB4.SA", "name": "Itaú Unibanco PN"},
    {"symbol": "BBDC4.SA", "name": "Bradesco PN"},
    {"symbol": "ABEV3.SA", "name": "Ambev ON"},
]
ticker_options = [{'label': f"{t['symbol']} - {t['name']}", 'value': t['symbol']} for t in TICKERS]

# Layout dinâmico
def serve_layout():
    try:
        if has_request_context() and 'initial_portfolio' in session:
            session_data = session.get("initial_portfolio")
            decoded = orjson_loads(session_data)
        else:
            logger.info("Sem contexto de requisição ou dados de portfólio. Usando valores padrão.")
            decoded = {
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
                'dividends': {},
                'setor_pesos': {},
                'setor_pesos_financeiros': {},
                'individual_daily_returns': {},
                'portfolio_daily_return': {},
                'portfolio_name': 'Portfólio 1',
                'is_registered': session.get('is_registered', False) if has_request_context() else False,
                'plan_type': session.get('plan_type', 'free') if has_request_context() else 'free',
                'tickers_limit': session.get('tickers_limit', 5) if has_request_context() else 5
            }
    except Exception as e:
        logger.error(f"Erro ao constuir layout dinâmico: {e}")
        decoded = {}   

    return html.Div([
        # ALTERAÇÃO: Removido storage_options do dcc.Store
        # Motivo: A versão do Dash (3.0.4) não suporta storage_options, causando TypeError
        # Impacto: dcc.Store usará json padrão internamente; serialização com orjson será feita manualmente nos callbacks
        dcc.Store(id='data-store', 
                    data=orjson_dumps(decoded).decode("utf-8"),
                    storage_type='session'),
        # ALTERAÇÃO: Substituir html.H1 por dbc.Row para header com título, cards, dropdown e botão
        # Motivo: Adicionar representação do portfólio e funcionalidade de salvamento no header
        # Impacto: Integra cards com tickers, dropdown para nome e modal para salvar portfólio
        dbc.Row([
            dbc.Col(
                html.H1("Dashboard de Portfólio", className="mb-0"),
                width=4
            ),
            
            dbc.Col([
                # Dropdown e botão na parte superior, fora do retângulo
                html.Div([
                    dbc.Select(
                        id='portfolio-name-dropdown',
                        options=[{'label': 'Portfólio 1', 'value': 'Portfólio 1'}],
                        value='Portfólio 1',
                        className="mb-2",
                        style={
                            'width': '120px',  # Reduzido o tamanho
                            'fontSize': '10px',  # Reduzido o tamanho da fonte
                            'marginRight': '10px',  # Espaço entre dropdown e botão
                        }
                    ),
                    dbc.Button(
                        "Salvar Portfólio",
                        id='save-portfolio-button',
                        n_clicks=0,
                        color="success",
                        size="sm",
                        style={
                            'fontSize': '10px',  # Reduzido o tamanho da fonte
                            'padding': '3px 8px',  # Ajustado o padding para menor tamanho
                        }
                    ),
                ], style={
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'flex-end',
                    'marginBottom': '5px',  # Espaçamento abaixo dos elementos
                }),
                # Retângulo envolvente apenas para os cards
                html.Div([
                    html.Div(
                        id='portfolio-cards',
                        className="d-flex flex-wrap justify-content-center",
                        style={
                            'gap': '5px',
                            'maxWidth': '400px',
                            'flexGrow': 1,
                        }
                    ),
                ], style={
                    'border': '1px solid #dee2e6',
                    'borderRadius': '5px',
                    'padding': '10px',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'alignItems': 'center',
                    'backgroundColor': '#f8f9fa',
                }),
            ], width=8),
        ], className="mb-4 align-items-center"),
        # Modal para salvar portfólio
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Salvar Portfólio")),
            dbc.ModalBody([
                html.Label("Nome do Portfólio:", className="form-label"),
                dcc.Input(
                    id='portfolio-name-input',
                    type='text',
                    placeholder='Digite o nome do portfólio',
                    className='form-control mb-2',
                    style={'width': '100%'}
                ),
                html.Div(id='save-portfolio-message', className='mt-2')
            ]),
            dbc.ModalFooter([
                dbc.Button("Salvar", id='modal-save-button', color="primary"),
                dbc.Button("Cancelar", id='modal-cancel-button', color="secondary", n_clicks=0)
            ])
        ], id='save-portfolio-modal', is_open=False),
        
            # Bloco dos cards, transformando a coluna para ocupar a largura restante
            
        dbc.Col([  
            dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Retorno Total", className="card-title"),
                            html.P("12.3%", className="card-text", style={'fontSize': '24px', 'fontWeight': 'bold', 'color': '#198754'}),
                        ])
                    ], className="mb-3 shadow-sm"),
                    md=4
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Volatilidade", className="card-title"),
                            html.P("18.7%", className="card-text", style={'fontSize': '24px', 'fontWeight': 'bold', 'color': '#0d6efd'}),
                        ])
                    ], className="mb-3 shadow-sm"),
                    md=4
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Sharpe Ratio", className="card-title"),
                            html.P("0.82", className="card-text", style={'fontSize': '24px', 'fontWeight': 'bold', 'color': '#fd7e14'}),
                        ])
                    ], className="mb-3 shadow-sm"),
                    md=4
                )
            ])
        ], width=12),

        dbc.Row([
            # Coluna Esquerda (1/3)
            dbc.Col([
                # Novo: Adicionar dbc.Alert para mensagens de erro de ticker
                dbc.Alert(
                    id='ticker-error-alert',
                    is_open=False,
                    dismissable=True,
                    color='danger',
                    style={'marginBottom': '10px', 'fontSize': '12px'}
                ),
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
                    dcc.DatePickerSingle(
                        id='start-date-input',
                        first_day_of_week=1,
                        date=None,
                        day_size=30,
                        month_format='MMMM, YYYY',
                        display_format='DD/MM/YYYY',
                        className="me-2",
                        style={'width': '25%', 'fontSize': '12px', 'minWidth': '130px', 'position': 'relative', 'zIndex': 1000}
                    ),
                    dcc.DatePickerSingle(
                        id='end-date-input',
                        first_day_of_week=1,
                        date=None,
                        day_size=30,
                        month_format='MMMM, YYYY',
                        display_format='DD/MM/YYYY',
                        className="",
                        style={'width': '25%', 'fontSize': '12px', 'minWidth': '130px', 'position': 'relative', 'zIndex': 1000}
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

def init_dash(flask_app, portfolio_service):
    dash_app = Dash(
        __name__, 
        server=flask_app, 
        url_base_pathname='/dash/findash/',
        external_stylesheets=[dbc.themes.FLATLY]
        )
    #dash_app.enable_dev_tools(debug=True, dev_tools_hot_reload=True)
    dash_app.portfolio_service = portfolio_service
    dash_app.layout = serve_layout
    
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
    
    # Callbacks
    @dash_app.callback(
        [Output('price-table', 'data'),
        Output('data-store', 'data', allow_duplicate=True)],
        [Input('data-store', 'data'),
        Input('price-table', 'data')],
        State('price-table', 'data_previous'),
        prevent_initial_call='initial_duplicate'
    )
    def update_price_table(store_data, table_data, table_data_previous):
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        # Logar conteúdo inicial de store_data
        logger.info(f"Conteúdo de store_data: tickers={store_data.get('tickers')}, período=({store_data.get('start_date')} -> {store_data.get('end_date')})")

        # Verificar se store_data contém table_data válido antes de inicializar como vazio
        if not store_data or 'portfolio' not in store_data or not store_data['portfolio'] or ('table_data' not in store_data or not store_data['table_data']):
            logger.info("Inicializando store_data com dados padrão")
            initial_data = {
                'is_registered': session.get('is_registered', False),
                'plan_type': session.get('plan_type', 'free'),
                'tickers_limit': session.get('tickers_limit', 5),
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
                'portfolio_daily_return': {},
                'portfolio_name': 'Portfólio 1'
            }
            return [], orjson_dumps(initial_data).decode('utf-8')

        tickers = store_data.get('tickers', [])
        quantities = store_data.get('quantities', [])
        portfolio = store_data.get('portfolio', {})
        ibov = store_data.get('ibov', {})
        start_date = store_data.get('start_date')
        end_date = store_data.get('end_date')
        dividends = store_data.get('dividends', {})

        # Logar tickers e quantities
        logger.info(f"Tickers: {tickers}, Quantities: {quantities}")

        # Usar table_data do store_data se válido, mesmo que table_data seja None
        if table_data is None or (table_data_previous is None and 'table_data' in store_data and store_data['table_data']):
            table_data = store_data.get('table_data', [])
            logger.info(f"table_data carregado com {len(table_data)} linhas | tickers={tickers}")
            return table_data, orjson_dumps(store_data).decode('utf-8')

        new_quantities = quantities.copy()
        if table_data and table_data != table_data_previous:
            table_quantities = {row['ticker']: int(row['quantidade']) for row in table_data if row['ticker'] != 'Total'}
            new_quantities = [table_quantities.get(ticker, quantities[i] if i < len(quantities) else 1)
                            for i, ticker in enumerate(tickers)]

            try:
                result = calcular_metricas(portfolio, tickers, new_quantities, start_date, end_date, ibov, dividends=dividends)
                metrics = result['table_data']
            except Exception as e:
                logger.error(f"Erro ao calcular métricas: {e}")
                metrics = store_data.get('table_data', [])  # Preservar table_data existente
        else:
            metrics = store_data.get('table_data', [])  # Preservar table_data existente

        # Logar metrics
        logger.info(f"Métricas calculadas: {metrics}")

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

        # Logar dados finais
        logger.info(f"Retornando updated_table_data: {updated_table_data}")
        return updated_table_data, orjson_dumps(updated_store_data).decode('utf-8')

    @dash_app.callback(
        [Output('start-date-input', 'date'),
        Output('end-date-input', 'date')],
        Input('data-store', 'data'),
        prevent_initial_call=False
        )
    def carregar_datas_iniciais(store_data):
        """
        Preenche os inputs de data com os valores do dcc.Store ao iniciar o app.
        """
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data
            return store_data.get('start_date'), store_data.get('end_date')
        return None, None

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
                logger.info(f"Ticker {ticker_to_remove} removido")
                # ALTERAÇÃO: Serializar updated_portfolio com orjson_dumps antes de salvar
                # Motivo: Garante que os dados salvos usem orjson
                return orjson_dumps(updated_portfolio).decode('utf-8')
            except ValueError as e:
                logger.error(f"Erro ao remover ticker: {e}")
                # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
                # Motivo: Mantém consistência com a serialização manual
                return orjson_dumps(store_data).decode('utf-8')
        
        # ALTERAÇÃO: Serializar store_data com orjson_dumps ao retornar
        # Motivo: Mantém consistência com a serialização manual
        return orjson_dumps(store_data).decode('utf-8')

    @dash_app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('ticker-dropdown', 'value'),
         Output('ticker-error-alert', 'children'),
         Output('ticker-error-alert', 'is_open'),
         Output('ticker-dropdown', 'disabled')],
        Input('ticker-dropdown', 'value'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def add_ticker(selected_ticker, store_data):
        """
        Adiciona um ticker ao portfólio usando o PortfolioService, validando o limite de tickers.
        """
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not selected_ticker or not store_data:
            return no_update, None, no_update, no_update, no_update
        
        # Verificar limite de tickers
        tickers_limit = session.get('tickers_limit', 5)
        current_tickers = len(store_data['tickers'])
        if current_tickers >= tickers_limit:
            error_message = f"Limite de {tickers_limit} tickers atingido"
            logger.warning(error_message)
            return no_update, None, error_message, True, True
        
        try:
            updated_portfolio = dash_app.portfolio_service.add_ticker(store_data, selected_ticker, 1)
            logger.info(f"Ticker {selected_ticker} adicionado")
            return orjson_dumps(updated_portfolio).decode('utf-8'), None, no_update, False, False
        except ValueError as e:
            logger.error(f"Erro ao adicionar ticker: {e}")
            return no_update, None, str(e), True, current_tickers + 1 >= tickers_limit

    @dash_app.callback(
        Output('data-store', 'data', allow_duplicate=True),
        Input('update-period-button', 'n_clicks'),
        State('start-date-input', 'date'),
        State('end-date-input', 'date'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def update_period(n_clicks, start_date, end_date, store_data):
        """
        Atualiza o período do portfólio usando o PortfolioService.
        """
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not n_clicks or not start_date or not end_date or not store_data:
            return orjson_dumps(store_data).decode('utf-8') if store_data else None

        try:
            # Converter YYYY-MM-DD (formato retornado por dcc.DatePickerSingle) para YYYY-MM-DD
            start_date_formatted = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            end_date_formatted = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            updated_portfolio = dash_app.portfolio_service.update_portfolio_period(store_data, start_date_formatted, end_date_formatted)
            logger.info(f"Período atualizado: {start_date_formatted} a {end_date_formatted}")
            return orjson_dumps(updated_portfolio).decode('utf-8')
        except ValueError as e:
            logger.error(f"Erro ao atualizar período: {e}")
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
            return go.Figure()

        tickers = store_data['tickers']
        quantities = store_data['quantities']
        portfolio_values = store_data['portfolio_values']
        dividends = store_data.get('dividends', {})
        start_date = store_data['start_date']
        end_date = store_data['end_date']

        if not start_date or not end_date or not tickers:
            return go.Figure()

        metrics = dash_app.portfolio_service.calcular_metricas_mensais_anuais(tickers, quantities, portfolio_values, dividends, start_date, end_date)

        periods = metrics['periods']
        capital_gains = metrics['capital_gains']
        dividend_yields = metrics['dividend_yields']
        total_returns = metrics['total_returns']

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

        if not store_data or 'portfolio_values' not in store_data or 'tickers' not in store_data:
            return go.Figure()

        tickers = store_data['tickers']
        quantities = store_data['quantities']
        portfolio_values = store_data['portfolio_values']
        dividends = store_data.get('dividends', {})
        start_date = store_data['start_date']
        end_date = store_data['end_date']

        if not start_date or not end_date or not tickers:
            return go.Figure()

        metrics = dash_app.portfolio_service.calcular_dy_por_setor(tickers, quantities, portfolio_values, dividends, start_date, end_date)

        years = metrics['years']
        setores = metrics['setores']
        dy_por_setor_por_ano = metrics['dy_por_setor_por_ano']

        fig = go.Figure()
        colors = ['#FF9999', '#FF6666', '#FF3333']
        for idx, year in enumerate(years):
            dy_values = [dy_por_setor_por_ano[setor][year] for setor in setores]
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

        if not store_data or 'tickers' not in store_data or 'portfolio_values' not in store_data:
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
            return go.Figure()

        individual_returns = store_data['individual_returns']
        tickers = store_data['tickers']
        returns_df = pd.DataFrame({ticker: individual_returns.get(ticker, {}) for ticker in tickers})
        returns_df = returns_df.apply(pd.to_numeric, errors='coerce').dropna()

        if returns_df.empty or len(returns_df.columns) < 2:
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
            return go.Figure()

        individual_daily_returns = store_data['individual_daily_returns']
        portfolio_daily_return = store_data['portfolio_daily_return']
        tickers = store_data['tickers']
        
        returns_df = pd.DataFrame({ticker: individual_daily_returns.get(ticker, {}) for ticker in tickers})
        returns_df = returns_df.apply(pd.to_numeric, errors='coerce').dropna()
        returns_df['Portfolio'] = pd.Series(portfolio_daily_return).reindex(returns_df.index).fillna(0)

        volatilities = returns_df.std() * (252 ** 0.5)

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
    
    # ALTERAÇÃO: Callback para atualizar cards e dropdown, e controlar modal
    # Motivo: Exibir tickers no header, nome do portfólio e abrir/fechar modal
    # Impacto: Integra cards dinâmicos e controle do modal
    @dash_app.callback(
        [Output('portfolio-cards', 'children'),
         Output('portfolio-name-dropdown', 'options'),
         Output('portfolio-name-dropdown', 'value'),
         Output('save-portfolio-modal', 'is_open'),
         Output('save-portfolio-button', 'disabled')],
        [Input('data-store', 'data'),
         Input('save-portfolio-button', 'n_clicks'),
         Input('modal-cancel-button', 'n_clicks'),
         Input('modal-save-button', 'n_clicks')],
        [State('save-portfolio-modal', 'is_open')],
        prevent_initial_call=False
    )
    def update_header_and_modal(store_data, save_clicks, cancel_clicks, save_modal_clicks, is_open):
        """
        Atualiza cards, dropdown, modal e desabilita botão de salvamento com base no plano.
        """
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        tickers = store_data.get('tickers', []) if store_data else []
        portfolio_name = store_data.get('portfolio_name', 'Portfólio 1') if store_data else 'Portfólio 1'
        plan_type = session.get('plan_type', 'free').capitalize()

        # Criar cards de tickers e exibir plano
        cards = [
            html.Div([
                html.Div([
                    dbc.Card(
                        html.Span(
                            ticker.replace('.SA', ''),
                            style={
                                'fontSize': '10px',
                                'fontWeight': 'bold',
                                'whiteSpace': 'nowrap',
                                'overflow': 'hidden',
                                'textOverflow': 'ellipsis',
                                'display': 'block',
                                'textAlign': 'center'
                            }
                        ),
                        body=True,
                        style={
                            'width': '60px',
                            'height': '30px',
                            'backgroundColor': '#e9ecef',
                            'display': 'flex',
                            'alignItems': 'center',
                            'justifyContent': 'center',
                            'margin': '2px',
                            'border': '1px solid #dee2e6',
                            'borderRadius': '3px'
                        }
                    ) for ticker in tickers
                ], className="d-flex flex-wrap justify-content-center"),
                html.Span(
                    f"Plano: {plan_type}",
                    style={
                        'fontSize': '10px',
                        'fontWeight': 'bold',
                        'marginTop': '5px',
                        'color': '#495057'
                    }
                )
            ])
        ]
        dropdown_options = [{'label': portfolio_name, 'value': portfolio_name}]
        dropdown_value = portfolio_name

        # Desabilitar botão de salvamento para usuários não cadastrados
        is_registered = session.get('is_registered', False)
        plan_type = session.get('plan_type', 'free')
        save_button_disabled = not is_registered or plan_type != 'registered'

        # Controle do modal
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        if triggered_id == 'save-portfolio-button' and save_clicks:
            return cards, dropdown_options, dropdown_value, True, save_button_disabled
        elif triggered_id in ['modal-cancel-button', 'modal-save-button'] and (cancel_clicks or save_modal_clicks):
            return cards, dropdown_options, dropdown_value, False, save_button_disabled

        return cards, dropdown_options, dropdown_value, is_open, save_button_disabled

    # ALTERAÇÃO: Callback para salvar portfólio via modal
    # Motivo: Enviar requisição POST a /save-portfolio com nome do portfólio
    # Impacto: Atualiza data-store com nome do portfólio e fecha modal
    @dash_app.callback(
        [Output('save-portfolio-message', 'children'),
        Output('data-store', 'data', allow_duplicate=True),
        Output('portfolio-name-dropdown', 'options', allow_duplicate=True),
        Output('portfolio-name-dropdown', 'value', allow_duplicate=True)],
        Input('modal-save-button', 'n_clicks'),
        [State('portfolio-name-input', 'value'),
        State('data-store', 'data')],
        prevent_initial_call=True
    )
    def save_portfolio(n_clicks, portfolio_name, store_data):
        """
        Salva o portfólio diretamente no banco usando PortfolioService, com dados do dcc.Store.
        """
        if not n_clicks:
            return no_update, no_update, no_update, no_update

        if not portfolio_name:
            return html.Div('Nome do portfólio obrigatório', className='text-danger'), no_update, no_update, no_update

        # Verificar se o usuário é cadastrado
        is_registered = session.get('is_registered', False)
        plan_type = session.get('plan_type', 'free')
        user_id = session.get('user_id')
        if not is_registered or plan_type != 'registered' or not user_id:
            error_message = "Salvamento restrito a usuários cadastrados"
            logger.warning(error_message)
            return html.Div(error_message, className='text-danger'), no_update, no_update, no_update

        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        try:
            # Criar portfólio com dados essenciais do dcc.Store
            portfolio = {
                'tickers': store_data.get('tickers', []),
                'quantities': store_data.get('quantities', []),
                'start_date': store_data.get('start_date', ''),
                'end_date': store_data.get('end_date', ''),
                'name': portfolio_name
            }
            # Salvar diretamente usando PortfolioService
            dash_app.portfolio_service.save_portfolio(user_id, portfolio, portfolio_name)
            # Atualizar store_data com o novo nome
            store_data['portfolio_name'] = portfolio_name
            logger.info(f"Portfólio '{portfolio_name}' salvo diretamente para user_id {user_id}")
            # Atualizar dropdown
            dropdown_options = [{'label': portfolio_name, 'value': portfolio_name}]
            return (
                html.Div('Portfólio salvo com sucesso', className='text-success'),
                orjson_dumps(store_data).decode('utf-8'),
                dropdown_options,
                portfolio_name
            )
        except ValueError as e:
            logger.error(f"Erro ao salvar portfólio: {e}")
            return html.Div(f'Erro: {str(e)}', className='text-danger'), no_update, no_update, no_update

    return dash_app