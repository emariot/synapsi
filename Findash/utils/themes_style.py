def build_theme_styles(theme: str):
    """
    Retorna os estilos usados para o tema especificado ('dark' ou 'light').

    Args:
        theme (str): "dark" ou "light".

    Returns:
        dict: Dicionário com todos os estilos usados no callback.
    """
    if theme == "dark":
        paper_border = "1px solid #444"
        background_color_paper = "#1a1b1e"
        background_color_table = "#1a1b1e"
        font_color = "#ffffff"
        background_color_header = "#2c2e33"
        background_color_odd_rows = "#2c2e33"
        kpi_text_color = "#b9c7e2"
        kpi_icon_bg = "#b9c7e2"
        kpi_icon_color = "#000"
        left_column_bg = "#2c2e33"
    else:
        paper_border = "1px solid #dee2e6"
        background_color_paper = "#ffffff"
        background_color_table = "#ffffff"
        font_color = "#212529"
        background_color_header = "#f8f9fa"
        background_color_odd_rows = "#f2f2f2"
        kpi_text_color = "#1e3a8a"
        kpi_icon_bg = "#1e3a8a"
        kpi_icon_color = "#fff"
        left_column_bg = "#f5f5f5"

    paper_style = {
        "display": "flex",
        "flexWrap": "wrap",
        "justifyContent": "center",
        "gap": "5px",
        "maxWidth": "100%",
        "border": paper_border,
        "borderRadius": "5px"
    }

    table_style = {
        "overflowX": "auto",
        "marginTop": "20px",
        "height": "200px",
        "overflowY": "auto",
        "border": paper_border,
        "backgroundColor": background_color_table
    }

    cell_style = {
        "fontSize": "12px",
        "textAlign": "center",
        "minWidth": "50px",
        "padding": "3px",
        "color": font_color,
        "backgroundColor": background_color_table,
    }

    header_style = {
        "fontWeight": "bold",
        "position": "sticky",
        "top": 0,
        "zIndex": 1,
        "backgroundColor": background_color_header,
        "color": font_color
    }

    data_conditional = [
        {"if": {"row_index": "odd"}, "backgroundColor": background_color_odd_rows},
        {"if": {"column_id": "acao"}, "cursor": "pointer", "color": "#4dabf7" if theme == "dark" else "#007bff"},
        {"if": {"column_id": "acao", "state": "active"}, "color": "#ff6b6b" if theme == "dark" else "#dc3545"}
    ]

    left_column_style = {
        "maxHeight": "750px",
        "overflow": "hidden",
        "backgroundColor": left_column_bg,
        "border": paper_border,
        "padding": "8px",
        "marginTop": "5px"
    }

    kpi_card_style = {
        "minWidth": "170px",
        "height": "70px",
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "padding": "8px",
        "backgroundColor": background_color_header,
        "borderColor": paper_border,
        "--kpi-text-color": kpi_text_color,
        "--kpi-icon-bg-color": kpi_icon_bg,
        "--kpi-icon-color": kpi_icon_color
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
        "backgroundColor": background_color_table
    }

    graph_paper_style = {
        "backgroundColor": background_color_table,
        "border": paper_border,
        "marginBottom": "10px",
        "marginRight": "10px"
    }

    return {
        "paper_style": paper_style,
        "table_style": table_style,
        "cell_style": cell_style,
        "header_style": header_style,
        "data_conditional": data_conditional,
        "left_column_style": left_column_style,
        "kpi_card_style": kpi_card_style,
        "kpi_cards_style": kpi_cards_style,
        "graph_paper_style": graph_paper_style,
    }
