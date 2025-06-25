
def get_figure_theme(theme: str = "light"):
    is_dark = theme == "dark"
    font_color = "#FFFFFF" if is_dark else "#212529"
    grid_color = "rgba(128, 128, 128, 0.2)"
    zero_line = {
        "zeroline": True,
        "zerolinecolor": "rgba(128, 128, 128, 0.3)",
        "zerolinewidth": 1
    }
    # Paletas de cores
    pastel_colors = [
        "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", 
        "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"   
    ]
    vibrant_colors = [
        "#5e44f6", "#bc0000", "#26d416", "#ffa600", "#ff6361",
        "#bc5090", "#58508d", "#003f5c", "#f95d6a", "#ffa07a"
    ]

    line_colors = {
        "portfolio": vibrant_colors[0] if is_dark else pastel_colors[0],
        "ibov": vibrant_colors[1] if is_dark else pastel_colors[1]
    }
    color_sequence = vibrant_colors if is_dark else pastel_colors

    return {
        "template": "plotly_dark" if is_dark else "plotly_white",
        "font": dict(family="Helvetica", size=10, color=font_color),
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": dict(l=50, r=20, t=40, b=10),
        "legend": dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=10, color=font_color),
            bgcolor="rgba(0,0,0,0)"
        ),
        "xaxis": dict(
            title=dict(font=dict(color=font_color, size=10, family="Helvetica")),
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
        "line_colors": line_colors,
        "color_sequence": color_sequence
    }
