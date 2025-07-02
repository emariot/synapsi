from dash import Dash, html, dcc, Output, Input, State, callback, no_update, dash_table
import plotly.graph_objects as go
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import dash_bootstrap_components as dbc
from Findash.modules.metrics import calcular_metricas
from Findash.modules.components import KpiCard, GraphPaper, IconTooltip, build_portfolio_cards
from Findash.utils.formatting import format_kpi
from datetime import datetime, timedelta
import pandas as pd
from Findash.services.portfolio_services import PortfolioService
from utils.serialization import orjson_dumps, orjson_loads
from flask import session, has_request_context
from Findash.callbacks.tables import register_table_callbacks
from Findash.callbacks.graphs import register_graph_callbacks
from Findash.callbacks.kpis_cards import register_kpis_card

from Findash.utils.logging_tools import logger, log_callback

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
            portfolio_data = orjson_loads(session_data)
        else:
            logger.info("Sem contexto de requisição ou dados de portfólio. Usando valores padrão.")
            portfolio_data = {
                'tickers': [],
                'quantities': [],
                #'portfolio': {},
                #'ibov': {},
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
            }
        # Metadados do usuário
        client_config = {
            'is_registered': session.get('is_registered', False) if has_request_context() else False,
            'plan_type': session.get('plan_type', 'free') if has_request_context() else 'free',
            'tickers_limit': session.get('tickers_limit', 5) if has_request_context() else 5
        }
    except Exception as e:
        logger.error(f"Erro ao constuir layout dinâmico: {e}")
        portfolio_data = {}  
        client_config = {} 

    # Serializa para JSON em bytes
    json_bytes = orjson_dumps(portfolio_data)

    # Tamanho em bytes e KB
    tamanho_bytes = len(json_bytes)
    tamanho_kb = tamanho_bytes / 1024

    print(f"Tamanho dos dados no Store: {tamanho_bytes} bytes ({tamanho_kb:.2f} KB)")

    # Extrair KPIs do portfolio_data
    kpis = portfolio_data.get("kpis", {})
    start_date = portfolio_data.get("start_date", {})
    end_date = portfolio_data.get("end_date", {})

    # Extrair table_data do portfolio_data
    table_data = portfolio_data.get('table_data', [])

    # Header: Portfólio Cards, dropdown portfólio, bt salvar portfólio
    tickers = portfolio_data.get("tickers", [])
    plan_type = client_config.get("plan_type", "free").capitalize()
    is_registered = client_config.get('is_registered', False) if has_request_context() else False
    portfolio_name = portfolio_data.get('portfolio_name', 'Portfólio 1')
    save_button_disabled = not is_registered or plan_type.lower() != 'registered'

    return dmc.MantineProvider(
        id = "mantine-provider",
        forceColorScheme="light",
        theme={
            "primaryColor":"indigo",
            "components": {
                "Button": {"styles": {"root": {"fontSize": "10px", "padding": "3px 8px"}}},
                "Select": {"styles": {"input": {"fontSize": "10px"}}},      
            
                },
            },
            children=[
                dcc.Store(
                    id='data-store', 
                    data=orjson_dumps(portfolio_data).decode("utf-8"),
                    storage_type='session',
                ),
                dcc.Store(
                    id='client-config',
                    data=client_config,
                    storage_type='session'
                ),
                dcc.Store(id="theme-store", data="light",storage_type="session"),
                dmc.Grid(
                    gutter="sm",
                    style={"margin": "10px"}, 
                    children = [
                        # Coluna do título "FinDash" (2/12)
                        dmc.GridCol(
                            span={"base": 12, "md": 2},
                            children=dmc.Title(
                                'FinDash', 
                                order=1, 
                                style={ "margin": 0, "textAlign": "left", "paddingLeft": "0"}
                            ),
                        ),
                        # Coluna do portfolio-cards (9/12)
                        dmc.GridCol(
                            span={"base": 12, "md": 7},
                            children=build_portfolio_cards(tickers, plan_type)
                        ),
                        # Coluna do dropdown, botão e ActionIcons (3/12)
                        dmc.GridCol(
                            span={"base": 12, "md": 3},
                            children=dmc.Stack(
                                gap="xs",
                                style={"alignItems": "stretch", "width": "100%", "paddingRight": "0"},
                                children=[
                                    dmc.Select(
                                        id="portfolio-name-dropdown",
                                        data=[
                                            {"label": "Portfólio 1","value": "Portfólio 1"},
                                        ],
                                        value=portfolio_name,
                                        style={"width": "100%"},
                                        size="sm",
                                    ),  
                                    dmc.Button(
                                        id="save-portfolio-button",
                                        children="Salvar Portfólio",
                                        color="green",
                                        size="xs",
                                        fullWidth=True,
                                        disabled=save_button_disabled,
                                    ),
                                    dmc.Group(
                                        gap="xs",    
                                        justify="flex-end",
                                        style={"width": "100%"},
                                        
                                        children=[
                                            IconTooltip("settings-btn", "tabler:settings", "Configurações"),
                                            IconTooltip("reports-btn", "tabler:report", "Relatórios"),
                                            IconTooltip("alerts-btn", "tabler:bell", "Alertas"),
                                            IconTooltip("theme-toggle", "tabler:sun", "Alternar Tema", iconify_id="theme-icon"),
                                        ],
                                    ),
                                ],   
                            ),       
                        ),
                    ],
                ),

                #Modal para salvar portfólio
                dmc.Modal(
                    id="save-portfolio-modal",
                    opened=False,
                    title="Salvar Portfólio",
                    centered=True,
                    size="sm",
                    children=[
                        dmc.TextInput(
                            id="portfolio-name-input",
                            label="Nome do Portfólio",
                            placeholder="Digite o nome do portfólio",
                            style={"marginBottom": "10px"},
                    ),
                    html.Div(id="save-portfolio-message", style={"marginBottom": "10px"}),
                    dmc.Group(
                        justify="flex-end",
                        gap="xs",
                        children=[
                            dmc.Button(
                                children="Cancelar",
                                id="modal-cancel-button",
                                color="red",
                                size="xs",
                                variant="outline",
                            ),
                            dmc.Button(
                                children="Salvar",
                                id="modal-save-button",
                                color="green",
                                size="xs",
                            ),
                        ],
                    ),
                ],
            ),
            # Abas principais
            dmc.Tabs(
                id="main-tabs",
                value="geral",
                children=[
                    dmc.TabsList(
                        children=[
                            dmc.TabsTab("Geral", value="geral"),
                            dmc.TabsTab("Rentabilidade", value="rentabilidade"),
                            dmc.TabsTab("Diversificação", value="diversificacao"),
                            dmc.TabsTab("Risco", value="risco"),
                            dmc.TabsTab("IA", value="ia"),
                            dmc.TabsTab("Avançado", value="avancado"),
                        ],
                    ),
                    # Aba Geral
                    dmc.TabsPanel(
                        value="geral",
                        children=[
                            # Bloco dos cards, transformando a coluna para ocupar a largura restante
                            dmc.Grid(
                                gutter='sm',
                                children=[
                                    dmc.GridCol(
                                        span={"base":12, "md":12},
                                        children=dmc.Group(
                                            id="kpi-cards",
                                            style={
                                                "width": "100%",
                                                "display": "flex",
                                                "flexDirection": "row",
                                                "flexWrap": "nowrap",
                                                "overflowX": "auto",
                                                "gap": "12px",
                                                "padding": "8px 0",
                                                "alignItems": "center",
                                                "paddingLeft": "12px",
                                                "backgroundColor": "#ffffff"
                                            },
                                            children=[
                                                KpiCard(
                                                    kpi_name="Sharpe",
                                                    value=format_kpi("sharpe", kpis.get("sharpe")),
                                                    icon="tabler:chart-line",
                                                    tooltip="Sharpe Ratio mede o retorno ajustado ao risco",
                                                    id="kpi-sharpe"
                                                ),
                                                KpiCard(
                                                    kpi_name="Sortino",
                                                    value=format_kpi("sortino", kpis.get("sortino")),
                                                    icon="tabler:chart-bar",                                                    
                                                    tooltip="Sortino Ratio ajusta o retorno ao risco de downside",
                                                    id="kpi-sortino"
                                                ),
                                                KpiCard(
                                                    kpi_name="Retorno",
                                                    value=format_kpi("retorno_medio_anual", kpis.get("retorno_medio_anual")),
                                                    icon="tabler:arrow-up",                                                    
                                                    tooltip="Retorno médio anualizado do portfólio",
                                                    id="kpi-retorno"
                                                ),
                                                KpiCard(
                                                    kpi_name="Volat",
                                                    value=format_kpi("volatilidade", kpis.get("volatilidade")),
                                                    icon="tabler:activity",                                                    
                                                    tooltip="Volatilidade anualizada em percentual",                                                   
                                                    id="kpi-volat"

                                                ),
                                                KpiCard(
                                                    kpi_name="Drawdown",
                                                    value=format_kpi("max_drawdown", kpis.get("max_drawdown")),
                                                    icon="tabler:arrow-down",                                                    
                                                    tooltip="Maior perda percentual do portfólio",                                                  
                                                    id="kpi-drawdown"
                                                ),
                                                KpiCard(
                                                    kpi_name="Alpha",
                                                    value=format_kpi("alpha", kpis.get("alpha")),
                                                    icon="tabler:star",                                                    
                                                    tooltip="Excesso de retorno sobre o benchmark",                                                    
                                                    id="kpi-alpha"
                                                ),
                                                KpiCard(
                                                    kpi_name="Beta",
                                                    value=format_kpi("beta", kpis.get("beta")),
                                                    icon="tabler:scale",                                                    
                                                    tooltip="Sensibilidade ao mercado (beta)",                                                  
                                                    id="kpi-beta"
                                                ),
                                            ]
                                        )
                                    )
                                ]
                            ),                         
                        
                            dmc.Grid(
                                gutter="sm",
                                id="main-grid",
                                style={
                                    "marginLeft": "12px",             
                                },
                                children=[
                                    #Coluna Esquerda (1/3)
                                    dmc.GridCol(
                                        span={"base": 12, "md": 4},
                                        id="left-column",
                                        style={
                                            "maxHeight": "750px", 
                                            "overflow": "hidden",
                                            "backgroundColor": "#f5f5f5",
                                            "border": "1px solid #dee2e6",
                                            "padding": "8px",
                                            "marginTop": "5px", 
                                                                                    
                                        },
                                        children=[
                                            dmc.Alert(
                                                id='ticker-error-alert',
                                                children="Ticker inválido ou limite de tickers atingido.",
                                                color="red",
                                                hide=True,
                                                radius="md",
                                                withCloseButton=True,
                                                style={'marginBottom': '10px', 'fontSize': '12px'},
                                            ),
                                            dmc.Grid(
                                                gutter="xs",
                                                style={'marginBottom': '10px'},
                                                children=[
                                                    dmc.GridCol(
                                                        span={"base": 12, "md": 7},
                                                        children=dmc.Select(
                                                            id='ticker-dropdown',
                                                            label="Inclua novos Tickers",
                                                            data=ticker_options,
                                                            value=None,
                                                            searchable=True,
                                                            limit=10,
                                                            placeholder="Selecione um ticker",
                                                            style={'width': '100%'},
                                                            size="xs",
                                                            clearable=True,
                                                        ),
                                                    ),
                                                    dmc.GridCol(
                                                        span={"base": 12, "md": 5},
                                                        children=[
                                                            dmc.DatesProvider(
                                                                settings={'locale': 'pt'},
                                                                children=dmc.DatePickerInput(
                                                                    id='date-input-range-picker',
                                                                    value=[start_date,end_date],
                                                                    label="Selecione novo período",
                                                                    type="range",
                                                                    numberOfColumns=2,
                                                                    minDate="2020-01-01",  # Data mínima obrigatória
                                                                    maxDate="2025-12-31",  # Data máxima obrigatória
                                                                    dropdownType="calendar",
                                                                    size="xs",
                                                                    valueFormat="DD/MM/YYYY",
                                                                    style={'width': '100%'},                                   
                                                                ),
                                                            ),
                                                            dmc.Group(
                                                                justify="flex-end",
                                                                mt=5,
                                                                children=[
                                                                    dmc.Button(
                                                                        id='update-period-button',
                                                                        children="Atualizar Período",
                                                                        size="xs",
                                                                        color="indigo",
                                                                        variant="filled",
                                                                        n_clicks=0,
                                                                        style={'width': '100%'}
                                                                    )
                                                                ]
                                                            ),
                                                        ],
                                                    ),
                                                ]
                                            ),
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
                                                data=table_data,
                                                style_table={'overflowX': 'auto',                   
                                                            'height': '200px',
                                                            'border': '1px solid #dee2e6',
                                                            'overflowY': 'auto'
                                                            },
                                                fixed_rows={'headers': True},  
                                                style_cell={'fontSize': '12px', 
                                                            'textAlign': 'center', 
                                                            'minWidth': '50px',
                                                            'padding': '3px'
                                                },
                                                style_header={'fontWeight': 'bold', 
                                                            'position': 'sticky',
                                                            'top': 0,
                                                            'zIndex': 1
                                                            },
                                                style_data_conditional=[],
                                                editable=True
                                            ),
                                            
                                            dcc.Graph(id='portfolio-treemap', style={'width': '100%', 'height': '200px', 'marginTop': '10px'}),
                                            dcc.Graph(id='financial-treemap', style={'width': '100%', 'height': '200px', 'marginTop': '10px'})
                                        ]
                                    ),
                                    # Coluna Direita (2/3)
                                    dmc.GridCol(
                                        span={"base":12, "md": 8},
                                        id="right-column",
                                        children=[
                                            dmc.Box(
                                                children=[
                                                    GraphPaper("portfolio-ibov-line-paper", "portfolio-ibov-line"),
                                                    dmc.LoadingOverlay(
                                                        id="loading-overlay-ibov",
                                                        visible=True,
                                                        zIndex=1000,
                                                        overlayProps={"blur": 2},
                                                        loaderProps={"type": "bars", "color": "blue", "size": 20},
                                                        
                                                    ),
                                                ],
                                                pos="relative"
                                            ),
                                            dmc.Box(
                                                children=[
                                                    GraphPaper("individual-tickers-line-paper","individual-tickers-line"),
                                                    dmc.LoadingOverlay(
                                                        id="loading-overlay-individual",
                                                        visible=True,
                                                        zIndex=1000,
                                                        overlayProps={"blur": 2},
                                                        loaderProps={"type": "bars", "color": "blue", "size": 20},
                                                        
                                                    ),
                                                ],
                                                pos="relative"
                                            ),
                                            dmc.Box(
                                                children=[
                                                    GraphPaper("stacked-area-chart-paper", "stacked-area-chart"),
                                                    dmc.LoadingOverlay(
                                                        id="loading-overlay-area-chart",
                                                        visible=True,
                                                        zIndex=1000,
                                                        overlayProps={"blur": 2},
                                                        loaderProps={"type": "bars", "color": "blue", "size": 20},
                                                        
                                                    ),
                                                ],
                                                pos="relative"
                                            )
                                        ]                                        
                                    ),            
                                ]
                            ),

                        #     html.Div([
                        #                     # Linha de largura total para os três novos elementos
                        #     dbc.Row([
                        #         # Coluna para o Gráfico 1 (Capital Gains e Dividend Yield)
                        #         dbc.Col([
                        #             dcc.Graph(id='capital-dividend-chart', style={'width': '100%', 'height': '200px'})
                        #         ], md=4, className="p-2"),
                        #         # Placeholder para o Gráfico 2 (Dividendos por Setor)
                        #         dbc.Col([
                        #             dcc.Graph(id='dividend-by-sector-chart', style={'width': '100%', 'height': '200px'})
                        #         ], md=4, className="p-2"),
                        #         # Placeholder para a Tabela (Ranking de DY)
                        #         dbc.Col([
                        #             dcc.Graph(id='cumulative-gains-dividends-chart', style={'width': '100%', 'height': '200px'})
                        #         ], md=4, className="p-2"),
                        #     ], className="g-3"),
                        #     # Três Colunas Inferiores
                        #     dbc.Row([
                        #         dbc.Col([
                        #             dcc.Graph(id='sector-donut-charts', style={'width': '100%', 'height': '300px'})
                        #         ], md=4, className="p-2"),
                        #         dbc.Col([
                        #             dcc.Graph(id='correlation-heatmap', style={'width': '100%', 'height': '300px'})
                        #         ], md=4, className="p-2"),
                        #         dbc.Col([
                        #             dcc.Graph(id='volatility-chart', style={'width': '100%', 'height': '300px'})
                        #         ], md=4, className="p-2"),
                        #     ], className="g-3"),
                        # ],id="app-body", className="p-4 container-fluid")
                    ],
                ), 
                # Aba Rentabilidade - Placeholder
                dmc.TabsPanel(
                    value="rentabilidade",
                    children=[
                        dmc.Grid(
                            gutter="sm",
                            children=[
                                dmc.GridCol(
                                    span={"base": 12, "md": 12},
                                    children=[
                                        dmc.Text(
                                            "Funcionalidades de Rentabilidade em desenvolvimento.",
                                            size="lg",
                                            style={"textAlign": "center", "marginTop": "20px"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                # Aba Diversificação - Placeholder
                dmc.TabsPanel(
                    value="diversificacao",
                    children=[
                        dmc.Grid(
                            gutter="sm",
                            children=[
                                dmc.GridCol(
                                    span={"base": 12, "md": 12},
                                    children=[
                                        dmc.Text(
                                            "Funcionalidades de Diversificação em desenvolvimento.",
                                            size="lg",
                                            style={"textAlign": "center", "marginTop": "20px"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                # Aba de Risco - Placeholder
                dmc.TabsPanel(
                    value="risco",
                    children=[
                        dmc.Grid(
                            gutter="sm",
                            children=[
                                dmc.GridCol(
                                    span={"base": 12, "md": 12},
                                    children=[
                                        dmc.Text(
                                            "Funcionalidades de Rsico em desenvolvimento.",
                                            size="lg",
                                            style={"textAlign": "center", "marginTop": "20px"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                # Aba IA - Placeholder
                dmc.TabsPanel(
                    value="ia",
                    children=[
                        dmc.Grid(
                            gutter="sm",
                            children=[
                                dmc.GridCol(
                                    span={"base": 12, "md": 12},
                                    children=[
                                        dmc.Text(
                                            "Funcionalidades de IA em desenvolvimento.",
                                            size="lg",
                                            style={"textAlign": "center", "marginTop": "20px"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                # Aba Avançado - Placeholder
                dmc.TabsPanel(
                    value="avancado",
                    children=[
                        dmc.Grid(
                            gutter="sm",
                            children=[
                                dmc.GridCol(
                                    span={"base": 12, "md": 12},
                                    children=[
                                        dmc.Text(
                                            "Funcionalidades de ferramentas avançadas em desenvolvimento.",
                                            size="lg",
                                            style={"textAlign": "center", "marginTop": "20px"}
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),

            ],
        ),
    ],
)           

def init_dash(flask_app, portfolio_service):
    dash_app = Dash(
        __name__, 
        server=flask_app, 
        url_base_pathname='/dash/findash/',
        external_stylesheets=[],
        external_scripts=[
            "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.11.7/dayjs.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/dayjs/1.11.7/locale/pt.js",
            "/static/assets/dayjs-config.js",
        ]
    )
    #dash_app.enable_dev_tools(debug=True, dev_tools_hot_reload=True)
    dash_app.portfolio_service = portfolio_service
    dash_app.layout = serve_layout
    
    # Registrar callbacks modulares
    register_table_callbacks(dash_app)
    register_kpis_card(dash_app)
    register_graph_callbacks(dash_app)
    
    # Configurar o Flask subjacente para usar orjson em respostas JSON
    # Garante que os callbacks do Dash usem orjson para serializar respostas
    flask_app.json_encoder = orjson_dumps
    flask_app.json_decoder = orjson_loads
    dash_app.server.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    
    # Callbacks
    @dash_app.callback(
        [Output("mantine-provider", "forceColorScheme"),
        Output("theme-icon", "icon"),
        Output("theme-store", "data"),
        Output("portfolio-cards", "style"),
        Output("price-table", "style_table"),
        Output("price-table", "style_cell"),
        Output("price-table", "style_header"),
        Output("price-table", "style_data_conditional"),
        Output("left-column", "style"),
        Output("kpi-cards", "style"),
        Output("kpi-sharpe", "style"),
        Output("kpi-sortino", "style"),
        Output("kpi-retorno", "style"),
        Output("kpi-volat", "style"),
        Output("kpi-drawdown", "style"),
        Output("kpi-alpha", "style"),
        Output("kpi-beta", "style"),
        Output("portfolio-ibov-line-paper", "style"),
        Output("individual-tickers-line-paper", "style"),
        Output("stacked-area-chart-paper", "style")
        ],
        Input("theme-toggle", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True
    )
    @log_callback("toggle_theme")
    def toggle_theme(n_clicks, current_theme):
        if n_clicks is None or n_clicks == 0:
            return [no_update] * 20

        new_theme = "dark" if current_theme == "light" else "light"
        new_icon = "tabler:moon" if new_theme == "dark" else "tabler:sun"

        # Estilos para ambos os temas
        paper_style = {
            "display": "flex",
            "flexWrap": "wrap",
            "justifyContent": "center",
            "gap": "5px",
            "maxWidth": "100%",
            "border": "1px solid #444" if new_theme == "dark" else "1px solid #dee2e6",
            "borderRadius": "5px"
        }

        table_style = {
            "overflowX": "auto",
            "marginTop": "20px",
            "height": "200px",
            "overflowY": "auto",
            "border": "1px solid #444" if new_theme == "dark" else "1px solid #dee2e6",
            "backgroundColor": "#1a1b1e" if new_theme == "dark" else "#ffffff"
        }

        cell_style = {
            "fontSize": "12px",
            "textAlign": "center",
            "minWidth": "50px",
            "padding": "3px",
            "color": "#ffffff" if new_theme == "dark" else "#212529",
            "backgroundColor": "#1a1b1e" if new_theme == "dark" else "#ffffff",
        }

        header_style = {
            "fontWeight": "bold",
            "position": "sticky",
            "top": 0,
            "zIndex": 1,
            "backgroundColor": "#2c2e33" if new_theme == "dark" else "#f8f9fa",
            "color": "#ffffff" if new_theme == "dark" else "#212529"
        }

        data_conditional = [
            {"if": {"row_index": "odd"}, "backgroundColor": "#2c2e33" if new_theme == "dark" else "#f2f2f2"},
            {"if": {"column_id": "acao"}, "cursor": "pointer", "color": "#4dabf7" if new_theme == "dark" else "#007bff"},
            {"if": {"column_id": "acao", "state": "active"}, "color": "#ff6b6b" if new_theme == "dark" else "#dc3545"}
        ]

        left_column_style = {
            "maxHeight": "750px",
            "overflow": "hidden",
            "backgroundColor": "#2c2e33" if new_theme == "dark" else "#f5f5f5",
            "border": "1px solid #444" if new_theme == "dark" else "1px solid #dee2e6",
            "padding": "8px",
            "marginTop": "5px"
        }

        kpi_cards_style = {
            "width": "100%",
            "display": "flex",
            "flexDirection": "row",
            "flexWrap": "nowrap",
            "overflowX": "auto",
            "gap": "12px",
            "padding": "8px 0",
            "alignItems": "center",
            "paddingLeft": "12px",
            "backgroundColor": "#1a1b1e" if new_theme == "dark" else "#ffffff"
        }

        kpi_card_style = {
            "minWidth": "170px",
            "height": "70px",
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "padding": "8px",
            "backgroundColor": "#2c2e30" if new_theme == "dark" else "#f8f9fa",
            "borderColor": "#444" if new_theme == "dark" else "#dee2e6",
            "--kpi-text-color": "#b9c7e2" if new_theme == "dark" else "#1e3a8a",
            "--kpi-icon-bg-color":"#b9c7e2" if new_theme == "dark" else "#1e3a8a",
            "--kpi-icon-color": "#000" if new_theme == "dark" else "#fff"
            
        }
        graph_paper_style = {
            "backgroundColor": "#1a1b1e" if new_theme == "dark" else "#f5f5f5",
            "border": "1px solid #444" if new_theme == "dark" else "1px solid #dee2e6",
            "marginBottom": "10px",
            "marginRight": "10px"
        }

        return (
            new_theme,
            new_icon,
            new_theme,
            paper_style,
            table_style,
            cell_style,
            header_style,
            data_conditional,
            left_column_style,
            kpi_cards_style,
            kpi_card_style,
            kpi_card_style,
            kpi_card_style,
            kpi_card_style,
            kpi_card_style,
            kpi_card_style,
            kpi_card_style,
            graph_paper_style,
            graph_paper_style,
            graph_paper_style
        )

        # ALTERAÇÃO: Callback para atualizar cards e dropdown, e controlar modal
    # Motivo: Exibir tickers no header, nome do portfólio e abrir/fechar modal
    # Impacto: Integra cards dinâmicos e controle do modal
    # @dash_app.callback(
    #     [Output('portfolio-cards', 'children'),
    #     Output('portfolio-name-dropdown', 'options'),
    #     Output('portfolio-name-dropdown', 'value'),
    #     Output('save-portfolio-modal', 'opened'),
    #     Output('save-portfolio-button', 'disabled')],
    #     [Input('data-store', 'data'),
    #     Input('save-portfolio-button', 'n_clicks'),
    #     Input('modal-cancel-button', 'n_clicks'),
    #     Input('modal-save-button', 'n_clicks')],
    #     [State('save-portfolio-modal', 'opened')],
    # prevent_initial_call=False
    # )
    # @log_callback("update_header_and_modal")
    # def update_header_and_modal(store_data, save_clicks, cancel_clicks, save_modal_clicks, opened):
    #     """
    #     Atualiza cards, dropdown, modal e desabilita botão de salvamento com base no plano.
    #     """
    #     if store_data:
    #         store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

    #     tickers = store_data.get('tickers', []) if store_data else []
    #     portfolio_name = store_data.get('portfolio_name', 'Portfólio 1') if store_data else 'Portfólio 1'
    #     plan_type = session.get('plan_type', 'free').capitalize()

    #     # Criar cards de tickers e exibir plano
    #     children = [
    #         dmc.Group(
    #             style={
    #                 "position": "relative",  # Contexto para posicionamento absoluto
    #                 "minHeight": "60px",  # Espaço para texto fixo
    #                 "width": "100%",
    #                 "justifyContent": "center",  # Centraliza conteúdo horizontalmente
    #                 "alignItems": "center"  # Centraliza conteúdo verticalmente
    #             },
    #             children=[
    #                 dmc.Group(  # Grupo para os badges dos tickers
    #                     gap="4px",
    #                     style={
    #                         "flexWrap": "nowrap",
    #                         "display": "flex",
    #                         "flexDirection": "row",
    #                         "justifyContent": "center",
    #                         "paddingBottom": "30px"
    #                     },
    #                     children=[
    #                         dmc.Tooltip(
    #                             label=f"Detalhes de {ticker.replace('.SA', '')}",
    #                             position="top",
    #                             withArrow=True,
    #                             transitionProps={
    #                                 "transition": "scale", 
                          
    #                             },
    #                             children=[
    #                                 dmc.Badge(
    #                                     ticker.replace('.SA', ''),
    #                                     variant="filled",
    #                                     color="indigo",
    #                                     size="md",
    #                                     style={
    #                                         "borderRadius": "4px",
    #                                         "padding": "4px 8px",
    #                                         "margin": "0",
    #                                         "fontSize": "12px",
    #                                         "fontWeight": 500
    #                                     },
    #                                 )
    #                             ]
    #                         ) for ticker in tickers
    #                     ],
    #                 ),
    #                 dmc.Group(  # Grupo separado para o texto do plano
    #                     style={
    #                         "position": "absolute",  # Fixa na base
    #                         "bottom": "-5px",  # Distância da borda inferior
    #                         "width": "100%",
    #                         "justifyContent": "center"  # Centraliza texto
    #                     },
    #                     children=[
    #                         dmc.Text(
    #                             f"Plano: {plan_type}",
    #                             size="xs",
    #                             fw=700,
    #                             style={"color": "#495057" if plan_type.lower() == "light" else "#adb5bd"}
    #                         )
    #                     ]
    #                 )
    #             ]
    #         )
    #     ]
                        
        
    #     dropdown_options = [{'label': portfolio_name, 'value': portfolio_name}]
    #     dropdown_value = portfolio_name

    #     # Desabilitar botão de salvamento para usuários não cadastrados
    #     is_registered = session.get('is_registered', False)
    #     plan_type = session.get('plan_type', 'free')
    #     save_button_disabled = not is_registered or plan_type != 'registered'

    #     # Controle do modal
    #     ctx = dash.callback_context
    #     triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
    #     # Abrir modal ao clicar em "Salvar Portfólio"
    #     if triggered_id == 'save-portfolio-button' and save_clicks:
    #         return children, dropdown_options, dropdown_value, True, save_button_disabled
    #     # Fechar modal ao clicar em "Cancelar" ou "Salvar"
    #     elif triggered_id in ['modal-cancel-button', 'modal-save-button']:
    #         return children, dropdown_options, dropdown_value, False, save_button_disabled
    #     # Manter estado atual se não houver interação relevante
    #     return children, dropdown_options, dropdown_value, opened, save_button_disabled  

    # @dash_app.callback(
    #     [Output('price-table', 'data'),
    #     Output('data-store', 'data', allow_duplicate=True)],
    #     [Input('data-store', 'data'),
    #     Input('price-table', 'data')],
    #     State('price-table', 'data_previous'),
    #     prevent_initial_call='initial_duplicate'
    # )
    # def update_price_table(store_data, table_data, table_data_previous):
    #     if store_data:
    #         store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

    #     # Logar conteúdo inicial de store_data
    #     logger.info(f"Conteúdo de store_data: tickers={store_data.get('tickers')}, período=({store_data.get('start_date')} - {store_data.get('end_date')})")

    #     # Verificar se store_data contém table_data válido antes de inicializar como vazio
    #     if not store_data or 'portfolio' not in store_data or not store_data['portfolio'] or ('table_data' not in store_data or not store_data['table_data']):
    #         logger.info("Inicializando store_data com dados padrão")
    #         initial_data = {
    #             'is_registered': session.get('is_registered', False),
    #             'plan_type': session.get('plan_type', 'free'),
    #             'tickers_limit': session.get('tickers_limit', 5),
    #             'tickers': [],
    #             'quantities': [],
    #             'portfolio': {},
    #             'ibov': {},
    #             'start_date': None,
    #             'end_date': None,
    #             'portfolio_values': {},
    #             'portfolio_return': {},
    #             'individual_returns': {},
    #             'ibov_return': {},
    #             'table_data': [],
    #             'dividends': {ticker['symbol']: {} for ticker in TICKERS},
    #             'setor_pesos': {},
    #             'setor_pesos_financeiros': {},
    #             'individual_daily_returns': {},
    #             'portfolio_daily_return': {},
    #             'portfolio_name': 'Portfólio 1'
    #         }
    #         return [], orjson_dumps(initial_data).decode('utf-8')

    #     tickers = store_data.get('tickers', [])
    #     quantities = store_data.get('quantities', [])
    #     portfolio = store_data.get('portfolio', {})
    #     ibov = store_data.get('ibov', {})
    #     start_date = store_data.get('start_date')
    #     end_date = store_data.get('end_date')
    #     dividends = store_data.get('dividends', {})

    #     # Logar tickers e quantities
    #     logger.info(f"Tickers: {tickers}, Quantities: {quantities}")

    #     # Usar table_data do store_data se válido, mesmo que table_data seja None
    #     if table_data is None or (table_data_previous is None and 'table_data' in store_data and store_data['table_data']):
    #         table_data = store_data.get('table_data', [])
    #         logger.info(f"table_data carregado com {len(table_data)} linhas | tickers={tickers}")
    #         return table_data, orjson_dumps(store_data).decode('utf-8')

    #     new_quantities = quantities.copy()
    #     if table_data and table_data != table_data_previous:
    #         table_quantities = {row['ticker']: int(row['quantidade']) for row in table_data if row['ticker'] != 'Total'}
    #         new_quantities = [table_quantities.get(ticker, quantities[i] if i < len(quantities) else 1)
    #                         for i, ticker in enumerate(tickers)]

    #         try:
    #             result = calcular_metricas(portfolio, tickers, new_quantities, start_date, end_date, ibov, dividends=dividends)
    #             metrics = result['table_data']
    #         except Exception as e:
    #             logger.error(f"Erro ao calcular métricas: {e}")
    #             metrics = store_data.get('table_data', [])  # Preservar table_data existente
    #     else:
    #         metrics = store_data.get('table_data', [])  # Preservar table_data existente

    #     # Logar metrics
    #     logger.info(f"Métricas calculadas: {metrics}")

    #     ticker_quantities = dict(zip(tickers, new_quantities))
    #     updated_table_data = [row for row in metrics if row['ticker'] in tickers or row['ticker'] == 'Total']
    #     total_quantity = sum(ticker_quantities.values()) or 1
    #     for row in updated_table_data:
    #         if row['ticker'] != 'Total':
    #             row['quantidade'] = ticker_quantities.get(row['ticker'], 0)
    #             row['peso_quantidade_percentual'] = f"{(row['quantidade'] / total_quantity) * 100:.2f}%"
    #             row['acao'] = 'x'
    #         else:
    #             row['acao'] = "Total"
    #             row['quantidade'] = total_quantity
    #             row['peso_quantidade_percentual'] = "100.00%"

    #     updated_store_data = store_data.copy()
    #     updated_store_data['quantities'] = new_quantities
    #     if table_data and table_data != table_data_previous:
    #         updated_store_data.update(result)

    #     # Logar dados finais
    #     logger.info(f"Retornando updated_table_data: {updated_table_data}")
    #     return updated_table_data, orjson_dumps(updated_store_data).decode('utf-8')

    @dash_app.callback(
        [Output('save-portfolio-message', 'children'),
        Output('data-store', 'data', allow_duplicate=True),
        Output('portfolio-name-dropdown', 'options', allow_duplicate=True),
        Output('portfolio-name-dropdown', 'value', allow_duplicate=True),
        Output('save-portfolio-modal', 'opened', allow_duplicate=True)],  # Novo output para fechar o modal
        Input('modal-save-button', 'n_clicks'),
        [State('portfolio-name-input', 'value'),
        State('data-store', 'data')],
        prevent_initial_call=True
    )
    @log_callback("save_portfolio")
    def save_portfolio(n_clicks, portfolio_name, store_data):
        """
        Salva o portfólio diretamente no banco usando PortfolioService, com dados do dcc.Store, e fecha o modal.
        """
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update

        if not portfolio_name:
            return dmc.Text('Nome do portfólio obrigatório', color='red'), no_update, no_update, no_update, True

        # Verificar se o usuário é cadastrado
        is_registered = session.get('is_registered', False)
        plan_type = session.get('plan_type', 'free')
        user_id = session.get('user_id')
        if not is_registered or plan_type != 'registered' or not user_id:
            error_message = "Salvamento restrito a usuários cadastrados"
            logger.warning(error_message)
            return dmc.Text(error_message, color='red'), no_update, no_update, no_update, True

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
                dmc.Text('Portfólio salvo com sucesso', color='green'),
                orjson_dumps(store_data).decode('utf-8'),
                dropdown_options,
                portfolio_name,
                False  # Fechar o modal após salvar
            )
        except ValueError as e:
            logger.error(f"Erro ao salvar portfólio: {e}")
            return dmc.Text(f'Erro: {str(e)}', color='red'), no_update, no_update, no_update, True
        
    @dash_app.callback(
        Output('data-store', 'data', allow_duplicate=True),
        Input('update-period-button', 'n_clicks'),
        State('date-input-range-picker', 'value'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    @log_callback("update_period")
    def update_period(n_clicks, date_range, store_data):
        """
        Atualiza o período do portfólio usando o PortfolioService.
        """
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data
        if not n_clicks or not date_range or not store_data:
            return orjson_dumps(store_data).decode('utf-8') if store_data else None
        try:
            start_date_formatted = date_range[0]
            end_date_formatted = date_range[1]
            updated_portfolio = dash_app.portfolio_service.update_portfolio_period(store_data, start_date_formatted, end_date_formatted)
            return orjson_dumps(updated_portfolio).decode('utf-8')
        except ValueError as e:
            return orjson_dumps(store_data).decode('utf-8')
        
    @dash_app.callback(
        Output('portfolio-treemap', 'figure'),
        Input('data-store', 'data'),
        prevent_initial_call=False
    )
    @log_callback("update_portfolio_treemap")
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
    @log_callback("update_financial_treemap")
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
       
    # @dash_app.callback(
    #     Output('capital-dividend-chart', 'figure'),
    #     Input('data-store', 'data'),
    #     prevent_initial_call=False
    # )
    # @log_callback("update_capital_dividend_chart")
    # def update_capital_dividend_chart(store_data):
    #     """
    #     Gera um gráfico de colunas lado a lado com ganho de capital, dividend yield e retorno total.
    #     """
    #     # ALTERAÇÃO: Desserializar store_data com orjson_loads
    #     # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
    #     # Impacto: Permite acessar portfolio_values, dividends, etc. para gerar o gráfico
    #     if store_data:
    #         store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

    #     if not store_data or 'portfolio_values' not in store_data or 'tickers' not in store_data:
    #         return go.Figure()

    #     tickers = store_data['tickers']
    #     quantities = store_data['quantities']
    #     portfolio_values = store_data['portfolio_values']
    #     dividends = store_data.get('dividends', {})
    #     start_date = store_data['start_date']
    #     end_date = store_data['end_date']

    #     if not start_date or not end_date or not tickers:
    #         return go.Figure()

    #     metrics = dash_app.portfolio_service.calcular_metricas_mensais_anuais(tickers, quantities, portfolio_values, dividends, start_date, end_date)

    #     periods = metrics['periods']
    #     capital_gains = metrics['capital_gains']
    #     dividend_yields = metrics['dividend_yields']
    #     total_returns = metrics['total_returns']

    #     fig = go.Figure()
    #     fig.add_trace(go.Bar(
    #         x=periods,
    #         y=capital_gains,
    #         name='Ganho de Capital',
    #         marker_color='#F5CBA7',
    #         text=[f"{y:.1f}%" for y in capital_gains],
    #         textposition='auto'
    #     ))
    #     fig.add_trace(go.Bar(
    #         x=periods,
    #         y=dividend_yields,
    #         name='Dividend Yield',
    #         marker_color='#D35400',
    #         text=[f"{y:.1f}%" for y in dividend_yields if y > 0],
    #         textposition='auto'
    #     ))
    #     fig.add_trace(go.Scatter(
    #         x=periods,
    #         y=total_returns,
    #         mode='markers',
    #         name='Retorno Total',
    #         marker=dict(
    #             size=6,
    #             color='black',
    #             symbol='circle',
    #             line=dict(width=1, color='white')
    #         ),
    #         text=[f"{y:.1f}%" for y in total_returns],
    #         hoverinfo='text'
    #     ))
    #     fig.update_layout(
    #         title='Ganho de Capital e Dividend Yield',
    #         yaxis_title='Retorno (%)',
    #         barmode='group',
    #         bargap=0.3,
    #         height=200,
    #         margin=dict(l=40, r=40, t=60, b=40),
    #         legend=dict(
    #             x=0.5,
    #             y=1.1,
    #             xanchor='center',
    #             yanchor='bottom',
    #             bgcolor='rgba(255,255,255,0.5)',
    #             orientation='h'
    #         ),
    #         yaxis=dict(
    #             tickformat='.1f',
    #             ticksuffix='%',
    #             autorange=True
    #         )
    #     )
    #     return fig
    
    # @dash_app.callback(
    #     Output('dividend-by-sector-chart', 'figure'),
    #     Input('data-store', 'data'),
    #     prevent_initial_call=False
    # )
    # @log_callback("update_dividend_by_sector_chart")
    # def update_dividend_by_sector_chart(store_data):
    #     """
    #     Gera um gráfico de barras com o Dividend Yield por setor.
    #     """
    #     # ALTERAÇÃO: Desserializar store_data com orjson_loads
    #     # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
    #     # Impacto: Permite acessar portfolio_values, dividends, etc. para gerar o gráfico
    #     if store_data:
    #         store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

    #     if not store_data or 'portfolio_values' not in store_data or 'tickers' not in store_data:
    #         return go.Figure()

    #     tickers = store_data['tickers']
    #     quantities = store_data['quantities']
    #     portfolio_values = store_data['portfolio_values']
    #     dividends = store_data.get('dividends', {})
    #     start_date = store_data['start_date']
    #     end_date = store_data['end_date']

    #     if not start_date or not end_date or not tickers:
    #         return go.Figure()

    #     metrics = dash_app.portfolio_service.calcular_dy_por_setor(tickers, quantities, portfolio_values, dividends, start_date, end_date)

    #     years = metrics['years']
    #     setores = metrics['setores']
    #     dy_por_setor_por_ano = metrics['dy_por_setor_por_ano']

    #     fig = go.Figure()
    #     colors = ['#FF9999', '#FF6666', '#FF3333']
    #     for idx, year in enumerate(years):
    #         dy_values = [dy_por_setor_por_ano[setor][year] for setor in setores]
    #         fig.add_trace(go.Bar(
    #             x=setores,
    #             y=dy_values,
    #             name=year,
    #             marker_color=colors[idx % len(colors)],
    #             text=[f"{y:.1f}%" for y in dy_values if y > 0],
    #             textposition='auto'
    #         ))

    #     fig.update_layout(
    #         title='Dividend Yield por Setor',
    #         yaxis_title='Dividend Yield (%)',
    #         barmode='group',
    #         bargap=0.3,
    #         bargroupgap=0.0,
    #         height=200,
    #         margin=dict(l=40, r=40, t=60, b=40),
    #         legend=dict(
    #             x=0.5,
    #             y=1.1,
    #             xanchor='center',
    #             yanchor='bottom',
    #             bgcolor='rgba(255,255,255,0.5)',
    #             orientation='h'
    #         ),
    #         yaxis=dict(
    #             tickformat='.1f',
    #             ticksuffix='%',
    #             autorange=True
    #         ),
    #         annotations=[
    #             dict(
    #                 x=1,
    #                 y=-0.2,
    #                 xref="paper",
    #                 yref="paper",
    #                 text="* Anos incompletos foram anualizados",
    #                 showarrow=False,
    #                 font=dict(size=10)
    #             )
    #         ]
    #     )
    #     return fig
    
    # @dash_app.callback(
    #     Output('cumulative-gains-dividends-chart', 'figure'),
    #     Input('data-store', 'data'),
    #     prevent_initial_call=False
    # )
    # @log_callback("update_cumulative_gains_dividends_chart")
    # def update_cumulative_gains_dividends_chart(store_data):
    #     """
    #     Gera um gráfico de linhas mostrando o retorno total acumulado e o DY acumulado.
    #     """
    #     # ALTERAÇÃO: Desserializar store_data com orjson_loads
    #     # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
    #     # Impacto: Permite acessar portfolio_values, dividends, etc. para gerar o gráfico
    #     if store_data:
    #         store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

    #     if not store_data or 'tickers' not in store_data or 'portfolio_values' not in store_data:
    #         return go.Figure().update_layout(
    #             title="Retorno Total e DY Acumulados (%)",
    #             annotations=[dict(text="Sem dados", x=0.5, y=0.5, showarrow=False)]
    #         )

    #     tickers = store_data.get('tickers', [])
    #     quantities = store_data.get('quantities', [1] * len(tickers))
    #     portfolio_values = store_data.get('portfolio_values', {})
    #     dividends = store_data.get('dividends', {})
    #     start_date = store_data.get('start_date', '2024-01-01')
    #     end_date = store_data.get('end_date', '2025-04-23')

    #     start = pd.to_datetime(start_date)
    #     end = pd.to_datetime(end_date)

    #     portfolio_df = pd.DataFrame()
    #     for ticker in tickers:
    #         if ticker in portfolio_values and portfolio_values[ticker]:
    #             df = pd.DataFrame.from_dict(portfolio_values[ticker], orient='index', columns=[ticker])
    #             df.index = pd.to_datetime(df.index)
    #             portfolio_df = portfolio_df.join(df, how='outer') if not portfolio_df.empty else df
    #     portfolio_df = portfolio_df.ffill().loc[start:end]

    #     if portfolio_df.empty:
    #         return go.Figure().update_layout(
    #             title="Retorno Total e DY Acumulados (%)",
    #             annotations=[dict(text="Sem dados", x=0.5, y=0.5, showarrow=False)]
    #         )

    #     total_portfolio = pd.DataFrame()
    #     for ticker, qty in zip(tickers, quantities):
    #         if ticker in portfolio_df.columns:
    #             total_portfolio[ticker] = portfolio_df[ticker] * qty
    #     portfolio_series = total_portfolio.sum(axis=1)

    #     initial_value = portfolio_series.iloc[0]
    #     if initial_value == 0:
    #         return go.Figure().update_layout(
    #             title="Retorno Total e DY Acumulados (%)",
    #             annotations=[dict(text="Valor inicial zero", x=0.5, y=0.5, showarrow=False)]
    #         )

    #     gains_series = ((portfolio_series - initial_value) / initial_value) * 100

    #     dividend_dates = []
    #     dividend_totals = []
    #     cumulative_dividends = 0
    #     all_dates = pd.date_range(start=start, end=end, freq='D')
        
    #     for date in all_dates:
    #         date_str = date.strftime('%Y-%m-%d')
    #         daily_dividend = 0
    #         for ticker, qty in zip(tickers, quantities):
    #             if ticker in dividends and date_str in dividends[ticker]:
    #                 daily_dividend += dividends[ticker][date_str] * qty
    #         cumulative_dividends += daily_dividend
    #         dividend_dates.append(date)
    #         dividend_totals.append(cumulative_dividends)

    #     dividend_series = pd.Series(dividend_totals, index=dividend_dates)
    #     dividend_series = dividend_series.reindex(portfolio_series.index, method='ffill').fillna(0)
    #     dy_series = (dividend_series / initial_value) * 100

    #     total_return = gains_series + dy_series

    #     fig = go.Figure()
    #     fig.add_trace(go.Scatter(
    #         x=total_return.index,
    #         y=total_return.values,
    #         mode='lines',
    #         name='Retorno Total Acumulado (%)',
    #         line=dict(color='blue'),
    #         hovertemplate='%{x|%Y-%m-%d}: %{y:.2f}%'
    #     ))
    #     fig.add_trace(go.Scatter(
    #         x=dy_series.index,
    #         y=dy_series.values,
    #         mode='lines',
    #         name='DY Acumulado (%)',
    #         line=dict(color='green'),
    #         hovertemplate='%{x|%Y-%m-%d}: %{y:.2f}%'
    #     ))
    #     fig.update_layout(
    #         title="Retorno Total e DY Acumulados (%)",
    #         xaxis_title="Data",
    #         yaxis_title="Retorno Acumulado (%)",
    #         margin=dict(l=20, r=20, t=40, b=20),
    #         height=200,
    #         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    #     )
    #     return fig
        
    # @dash_app.callback(
    #     Output('sector-donut-charts', 'figure'),
    #     Input('data-store', 'data'),
    #     prevent_initial_call=False
    # )
    # @log_callback("update_sector_bar_chart")
    # def update_sector_bar_chart(store_data):
    #     # ALTERAÇÃO: Desserializar store_data com orjson_loads
    #     # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
    #     # Impacto: Permite acessar setor_pesos e setor_pesos_financeiros para gerar o gráfico
    #     if store_data:
    #         store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

    #     if not store_data or 'setor_pesos' not in store_data or 'setor_pesos_financeiros' not in store_data:
    #         return go.Figure()

    #     setor_pesos = store_data['setor_pesos']
    #     setor_pesos_financeiros = store_data['setor_pesos_financeiros']
        
    #     setor_abreviado = {
    #         "Petróleo, Gás e Biocombustíveis": "Petróleo\ne Gás",
    #         "Materiais Básicos": "Materiais\nBásicos",
    #         "Bens Industriais": "Bens\nIndustriais",
    #         "Consumo Não Cíclico": "Consumo\nNão Cíclico",
    #         "Consumo Cíclico": "Consumo\nCíclico",
    #         "Saúde": "Saúde",
    #         "Tecnologia e Comunicação": "Tech e\nComunicação",
    #         "Utilidade Pública": "Utilidade\nPública",
    #         "Financeiro e Outros": "Financeiro\ne Outros"
    #     }
        
    #     setores_completos = [s for s in setor_pesos.keys() if setor_pesos[s] > 0 or setor_pesos_financeiros[s] > 0]
    #     setores = [setor_abreviado[s] for s in setores_completos]
    #     pesos_quantidade = [setor_pesos[s] for s in setores_completos]
    #     pesos_financeiros = [setor_pesos_financeiros[s] for s in setores_completos]

    #     fig = go.Figure(data=[
    #         go.Bar(
    #             x=setores,
    #             y=pesos_quantidade,
    #             name='Peso por Quantidade',
    #             marker_color='#1f77b4',
    #             text=[f"{p:.1f}%" for p in pesos_quantidade],
    #             textposition='auto'
    #         ),
    #         go.Bar(
    #             x=setores,
    #             y=pesos_financeiros,
    #             name='Peso Financeiro',
    #             marker_color='#ff7f0e',
    #             text=[f"{p:.1f}%" for p in pesos_financeiros],
    #             textposition='auto'
    #         )
    #     ])
    #     fig.update_layout(
    #         title="Pesos por Setor",
    #         yaxis_title="Percentual (%)",
    #         barmode='group',
    #         bargap=0.15,
    #         bargroupgap=0.1,
    #         height=300,
    #         margin=dict(l=40, r=80, t=60, b=40),
    #         legend=dict(
    #             x=0.5,
    #             y=1.1,
    #             xanchor='center',
    #             yanchor='bottom',
    #             bgcolor='rgba(255,255,255,0.5)',
    #             orientation='h'
    #         )
    #     )
    #     return fig

    # @dash_app.callback(
    #     Output('correlation-heatmap', 'figure'),
    #     Input('data-store', 'data'),
    #     prevent_initial_call=False
    # )
    # @log_callback("update_correlation_heatmap")
    # def update_correlation_heatmap(store_data):
    #     # ALTERAÇÃO: Desserializar store_data com orjson_loads
    #     # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
    #     # Impacto: Permite acessar individual_returns para gerar o heatmap
    #     if store_data:
    #         store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

    #     if not store_data or 'individual_returns' not in store_data or not store_data['individual_returns']:
    #         return go.Figure()

    #     individual_returns = store_data['individual_returns']
    #     tickers = store_data['tickers']
    #     returns_df = pd.DataFrame({ticker: individual_returns.get(ticker, {}) for ticker in tickers})
    #     returns_df = returns_df.apply(pd.to_numeric, errors='coerce').dropna()

    #     if returns_df.empty or len(returns_df.columns) < 2:
    #         return go.Figure()
    #     correlation_matrix = returns_df.corr()

    #     fig = go.Figure(data=go.Heatmap(
    #         z=correlation_matrix.values,
    #         x=correlation_matrix.columns,
    #         y=correlation_matrix.index,
    #         colorscale='RdBu',
    #         zmin=-1, zmax=1,
    #         text=[[f"{val:.2f}" for val in row] for row in correlation_matrix.values],
    #         hoverinfo='text',
    #         colorbar=dict(title="Correlação")
    #     ))
    #     fig.update_layout(
    #         title="Correlação entre Tickers",
    #         xaxis_title="Tickers",
    #         yaxis_title="Tickers",
    #         margin=dict(l=40, r=40, t=60, b=40),
    #         height=300
    #     )
    #     return fig

    # @dash_app.callback(
    #     Output('volatility-chart', 'figure'),
    #     Input('data-store', 'data'),
    #     prevent_initial_call=False
    # )
    # @log_callback("update_volatility_chart")
    # def update_volatility_chart(store_data):
    #     # ALTERAÇÃO: Desserializar store_data com orjson_loads
    #     # Motivo: Dados do dcc.Store foram serializados com orjson_dumps; convertemos para dict
    #     # Impacto: Permite acessar individual_daily_returns e portfolio_daily_return para gerar o gráfico
    #     if store_data:
    #         store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

    #     if not store_data or 'individual_daily_returns' not in store_data or 'portfolio_daily_return' not in store_data:
    #         return go.Figure()

    #     individual_daily_returns = store_data['individual_daily_returns']
    #     portfolio_daily_return = store_data['portfolio_daily_return']
    #     tickers = store_data['tickers']
        
    #     returns_df = pd.DataFrame({ticker: individual_daily_returns.get(ticker, {}) for ticker in tickers})
    #     returns_df = returns_df.apply(pd.to_numeric, errors='coerce').dropna()
    #     returns_df['Portfolio'] = pd.Series(portfolio_daily_return).reindex(returns_df.index).fillna(0)

    #     volatilities = returns_df.std() * (252 ** 0.5)

    #     fig = go.Figure(go.Bar(
    #         x=volatilities.index,
    #         y=volatilities.values,
    #         text=[f"{v:.2f}%" for v in volatilities.values],
    #         textposition='auto',
    #         marker_color=['#1f77b4'] * len(tickers) + ['#ff7f0e'],
    #     ))
    #     fig.update_layout(
    #         title="Volatilidade Anualizada",
    #         yaxis_title="Volatilidade (%)",
    #         xaxis_title="Tickers",
    #         margin=dict(l=40, r=40, t=60, b=40),
    #         height=300,
    #         bargap=0.2
    #     )
    #     return fig
        
    return dash_app