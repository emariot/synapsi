
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
    dark_colors = [
         "#ffd15f",
         "#4c78a8",
         "#f58518",
         "#e45756",
         "#72b7b2",
         "#54a24b",
         "#b279a2",
         "#ff9da6",
         "#9d755d",
         "#bab0ac"  
    ]
    light_colors = [
         "#004172",
         "#3366cc",
         "#dc3912",
         "#ff9900",
         "#109618",
         "#990099",
         "#0099c6",
         "#dd4477",
         "#66aa00",
         "#b82e2e"
    ]

    line_colors = {
        "portfolio": dark_colors[0] if is_dark else light_colors[0],
        "ibov": dark_colors[1] if is_dark else light_colors[1]
    }
    color_sequence = dark_colors if is_dark else light_colors

    return {
        "template": "plotly_dark" if is_dark else "plotly_white",
        "font": dict(family="Helvetica", size=10, color=font_color),
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": dict(l=20, r=20, t=40, b=5),
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
