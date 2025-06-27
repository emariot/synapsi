# Findash/modules/components.py
from dash import dcc
from dash_iconify import DashIconify
import dash_mantine_components as dmc

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


