def get_color_sequence(theme: str):
    DARK_COLORS = [
        "#ffd15f", "#4c78a8", "#f58518", "#e45756", "#72b7b2",
        "#54a24b", "#b279a2", "#ff9da6", "#9d755d", "#bab0ac"
    ]
    LIGHT_COLORS = [
        "#004172", "#3366cc", "#dc3912", "#ff9900", "#109618",
        "#990099", "#0099c6", "#dd4477", "#66aa00", "#b82e2e"
    ]
    return DARK_COLORS if theme == "dark" else LIGHT_COLORS

def get_figure_theme(theme: str, title: str = None, yaxis_title: str = None):
    """
    Retorna dicionário com layout padrão para gráficos Plotly com base no tema.

    Args:
        theme (str): 'dark' ou 'light'.
        title (str): Título do gráfico.
        yaxis_title (str): Título do eixo Y.

    Returns:
        dict: layout padrão com estilo.
    """
    dark_mode = theme == "dark"
    font_color = "#FFFFFF" if dark_mode else "#212529"
    bg_color = "rgba(0,0,0,0)"

    layout = dict(
        font=dict(family="Helvetica", size=10, color=font_color),
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        margin=dict(l=20, r=20, t=40, b=5),
        hoverlabel=dict(
            bgcolor="#2c2c2c" if dark_mode else "#FFFFFF",
            font=dict(color=font_color, size=10, family="Helvetica"),
            bordercolor="rgba(0,0,0,0)"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=10, color=font_color),
            bgcolor=bg_color
        ),
        xaxis=dict(
            tickfont=dict(color=font_color),
            gridcolor="rgba(128, 128, 128, 0.2)",
            zeroline=False
        ),
        yaxis=dict(
            title=dict(
                text=yaxis_title or '',
                font=dict(size=10, color=font_color, family="Helvetica")
            ) if yaxis_title else None,
            tickfont=dict(color=font_color),
            gridcolor="rgba(128, 128, 128, 0.2)",
            zeroline=True,
            zerolinecolor="rgba(128, 128, 128, 0.3)",
            zerolinewidth=1
        )
    )

    if title:
        layout["title"] = dict(
            text=title,
            x=0.02, xanchor='left',
            y=0.98, yanchor='top',
            font=dict(size=12, family="Helvetica")
        )

    return layout