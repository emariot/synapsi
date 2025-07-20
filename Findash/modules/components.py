# Findash/modules/components.py
from dash import dcc
from dash_iconify import DashIconify
import dash_mantine_components as dmc
from Findash.utils.logging_tools import logger
from utils.serialization import orjson_dumps, orjson_loads
import redis

def build_portfolio_cards(tickers: list, plan_type: str, empresas_redis: redis.Redis, theme: str = "light"):
    """
    Retorna o componente `dmc.Paper` com badges dos tickers e nome do plano, adaptando-se ao tema.
    Inclui nome e setor econômico no tooltip, buscando dados diretamente do Redis (DB3).
    """
    is_dark = theme == "dark"
    plan_text_color = "#adb5bd" if is_dark else "#495057"

    if not tickers:
        logger.warning("Lista de tickers vazia, retornando componente vazio")
        return dmc.Paper(
            id="portfolio-cards",
            shadow="xs",
            p="sm",
            style={
                "width": "100%",
                "border": "1px solid #dee2e6",
                "borderRadius": "5px",
                "display": "flex",
                "flexDirection": "row",
                "flexWrap": "nowrap",
                "overflowX": "auto",
                "gap": "8px",
                "padding": "0px",
                "alignItems": "center",
                "margin": "0"
            },
            children=[
                dmc.Group(
                    style={
                        "position": "relative",
                        "minHeight": "60px",
                        "width": "100%",
                        "justifyContent": "center",
                        "alignItems": "center"
                    },
                    children=[
                        dmc.Text(
                            f"Plano: {plan_type}",
                            size="xs",
                            fw=700,
                            style={"color": plan_text_color}
                        )
                    ]
                )
            ]
        )

    ticker_badges = []
    for ticker in tickers:
        try:
            # Buscar dados diretamente do Redis (DB3)
            raw_data = empresas_redis.get(f"ticker_data:{ticker}")
            
            if raw_data:
                ticker_data = orjson_loads(raw_data)
                nome = ticker_data.get('nome', 'N/A')
                setor = ticker_data.get('setor_economico', 'N/A')
                tooltip_label = f"{ticker}\nNome: {nome}\nSetor:{setor}"
            else:
                logger.warning(f"Dados do ticker {ticker} não encontrados no Redis (DB3)")
                tooltip_label = f"Detalhes de {ticker}\nDados não disponíveis"
        except Exception as e:
            logger.error(f"Erro ao buscar dados do ticker {ticker} no Redis: {str(e)}")
            tooltip_label = f"Detalhes de {ticker}\nErro ao carregar dados"

        badge = dmc.Tooltip(
            label=tooltip_label,
            position="top",
            withArrow=True,
            transitionProps={"transition": "scale"},
            multiline=True,
            w=200,
            children=dmc.Badge(
                ticker,
                variant="filled",
                color="indigo",
                size="md",
                style={
                    "borderRadius": "4px",
                    "padding": "4px 8px",
                    "margin": "0",
                    "fontSize": "12px",
                    "fontWeight": 500
                }
            )
        )
        ticker_badges.append(badge)

    return dmc.Paper(
        id="portfolio-cards",
        shadow="xs",
        p="sm",
        style={
            "width": "100%",
            "border": "1px solid #dee2e6",
            "borderRadius": "5px",
            "display": "flex",
            "flexDirection": "row",
            "flexWrap": "nowrap",
            "overflowX": "auto",
            "gap": "8px",
            "padding": "0px",
            "alignItems": "center",
            "margin": "0"
        },
        children=[
            dmc.Group(
                style={
                    "position": "relative",
                    "minHeight": "60px",
                    "width": "100%",
                    "justifyContent": "center",
                    "alignItems": "center"
                },
                children=[
                    dmc.Group(
                        gap="4px",
                        style={
                            "flexWrap": "nowrap",
                            "display": "flex",
                            "flexDirection": "row",
                            "justifyContent": "center",
                            "paddingBottom": "30px"
                        },
                        children=ticker_badges
                    ),
                    dmc.Group(
                        style={
                            "position": "absolute",
                            "bottom": "-5px",
                            "width": "100%",
                            "justifyContent": "center"
                        },
                        children=[
                            dmc.Text(
                                f"Plano: {plan_type}",
                                size="xs",
                                fw=700,
                                style={"color": plan_text_color}
                            )
                        ]
                    )
                ]
            )
        ]
    )

def IconTooltip(action_id, icon_name, tooltip_label, icon_size=20, iconify_id=None):
    icon_props = {"icon": icon_name, "width": icon_size}
    if iconify_id:
        icon_props["id"] = iconify_id

    return dmc.Tooltip(
        label=tooltip_label,
        withArrow=True,
        transitionProps={"transition": "scale"},
        children=dmc.ActionIcon(
            id=action_id,
            children=[DashIconify(**icon_props)],
            variant="outline",
            size="sm",
        )
    )

def KpiCard(kpi_name, value, icon, tooltip, id=None):
    """
    Componente reutilizável para exibir KPIs em cards.
    
    Args:
        kpi_name (str): Nome do KPI (ex.: "Sharpe", "Volat.").
        value (float): Valor numérico do KPI.
        icon (str): Nome do ícone do DashIconify (ex.: "tabler:chart-line").
        color (str): Cor do ícone e texto (ex.: "#1e3a8a").
        tooltip (str): Texto do tooltip explicativo.
        id (str): ID único do componente para controle via callback.
    """  
    return dmc.Tooltip(
        label=tooltip,
        position="top",
        withArrow=True,
        transitionProps={"transition": "scale"},
        children=[
            dmc.Paper(
                id=id,
                withBorder=True,
                shadow="sm",
                radius="md",
                style={
                    "width": "170px",
                    "height": "70px",
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "padding": "8px",
                    "backgroundColor": "#f8f9fa"
                },
                children=[
                    dmc.Stack(
                        gap=0,  
                        align="start",
                        justify="center",
                        style={"flexGrow": 1},
                        children=[
                            dmc.Text(
                                value, 
                                size="lg", 
                                fw=700, 
                                style={"color": "var(--kpi-text-color, #1e3a8a)"},
                                id=f"{id}-value" if id else None
                                ),
                            dmc.Text(kpi_name, size="xs", fw=500, style={"color": "#6c757d"}),
                        ]
                    ),
                    dmc.Paper(
                        radius="md",
                        p="xs",
                        style={"backgroundColor": "var(--kpi-icon-bg-color, #1e3a8a)"},
                        children=DashIconify(icon=icon, width=22, color="var(--kpi-icon-color, #fff)")
                    )
                ]
            )
        ]
    )

GRAPH_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToAdd": ["toggleHover"],
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "toggleSpikelines", "zoom2d", "autoScale2d"
    ]
}

def GraphPaper(paper_id: str, graph_id: str, height="200px"):
    return dmc.Paper(
        id=paper_id,
        shadow="sm",
        radius="xs",
        p="sm",
        style={
            "backgroundColor": "#f5f5f5",  # estilo inicial (tema claro)
            "border": "1px solid #dee2e6",
            "marginBottom": "10px",
            "marginRight": "10px",
        },
        children=[
            dcc.Graph(
                id=graph_id,
                style={
                    "width": "100%",
                    "height": height,
                    "backgroundColor": "rgba(0,0,0,0)",
                },
                config=GRAPH_CONFIG,
            )
        ]
    )


