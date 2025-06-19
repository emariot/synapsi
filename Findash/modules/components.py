# Findash/modules/components.py
from dash_iconify import DashIconify
import dash_mantine_components as dmc


def KpiCard(kpi_name, value, icon, color, tooltip, is_percentage=False, id=None):
    """
    Componente reutilizável para exibir KPIs em cards.
    
    Args:
        kpi_name (str): Nome do KPI (ex.: "Sharpe", "Volat.").
        value (float): Valor numérico do KPI.
        icon (str): Nome do ícone do DashIconify (ex.: "tabler:chart-line").
        color (str): Cor do ícone e texto (ex.: "#1e3a8a").
        tooltip (str): Texto do tooltip explicativo.
        is_percentage (bool): Se True, formata o valor como percentual.
        id (str): ID único do componente para controle via callback.
    """
    formatted_value = f"{value:.2f}%" if is_percentage else f"{value:.2f}"
    return dmc.Tooltip(
        label=tooltip,
        position="top",
        withArrow=True,
        transitionProps={
            "transition": "scale"
        },
        children=[
            dmc.Card(
                id=id,
                withBorder=True,
                shadow="sm",
                radius="md",
                style={
                    "minWidth": "120px",
                    "height": "80px",
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center",
                },
                children=[
                    DashIconify(icon=icon, width=20, color=color),
                    dmc.Text(
                        formatted_value,
                        size="lg",
                        fw=700,
                        style={"color": "#dc2626" if value < 0 else color, "margin": "4px 0 0"}
                    ),
                    dmc.Text(
                        kpi_name,
                        size="xs",
                        fw=500,
                    )
                ]
            )
        ]
    )