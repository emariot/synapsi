GRAPH_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "toggleSpikelines"
    ]
}
def get_figure_theme(theme: str = "light"):
    is_dark = theme == "dark"
    font_color = "#FFFFFF" if is_dark else "#212529"
    grid_color = "rgba(128, 128, 128, 0.2)"
    zero_line = {
        "zeroline": True,
        "zerolinecolor": "rgba(128, 128, 128, 0.3)",
        "zerolinewidth": 1
    }
    line_colors = {
        "portfolio": "#5e44f6" if is_dark else "#1f77b4",
        "ibov": "#bc0000" if is_dark else "#ff7f0e"
    }

    return {
        "template": "plotly_dark" if is_dark else "plotly_white",
        "font": dict(family="Helvetica", size=12, color=font_color),
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": dict(l=40, r=40, t=50, b=40),
        "legend": dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color=font_color),
            bgcolor="rgba(0,0,0,0)"
        ),
        "xaxis": dict(
            title=dict(font=dict(color=font_color, size=12, family="Helvetica")),
            tickfont=dict(color=font_color),
            gridcolor=grid_color,
            **zero_line
        ),
        "yaxis": dict(
            title=dict(font=dict(color=font_color, size=10, family="Helvetica")),
            tickfont=dict(color=font_color),
            gridcolor=grid_color,
            **zero_line
        ),
        "line_colors": line_colors
    }
