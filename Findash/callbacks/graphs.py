from dash import Dash, Output, Input
import plotly.graph_objects as go
from utils.serialization import orjson_loads
from Findash.utils.plot_style import get_figure_theme
from Findash.utils.logging_tools import log_callback
import pandas as pd
from Findash.utils.logging_tools import logger
import orjson

def register_graph_callbacks(dash_app: Dash):
    """
    Registra callbacks relacionados a gráficos no Dash app.
    
    Args:
        dash_app (Dash): Instância do aplicativo Dash.
    """
    @dash_app.callback(
        Output('portfolio-ibov-line', 'figure'),
        Output('individual-tickers-line', 'figure'),
        Output('loading-overlay-ibov', 'visible'),
        Output('loading-overlay-individual', 'visible'),
        Input('data-store', 'data'),
        Input('theme-store', 'data'),
        prevent_initial_call=False
    )
    @log_callback("update_combined_return_lines")
    def update_combined_return_lines(store_data, theme):
        if not store_data:
            return go.Figure(), go.Figure(), False, False

        try:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data
        except orjson.JSONDecodeError:
            logger.error("Erro ao deserializar store_data")
            return go.Figure(), go.Figure(), False, False

        theme_config = get_figure_theme(theme)
        line_colors = theme_config.get("line_colors", {})
        color_sequence = theme_config.get("color_sequence", [])
        theme_config.pop("line_colors", None)
        theme_config.pop("color_sequence", None)

        # Gráfico Portfólio vs IBOV
        fig_ibov = go.Figure()
        if 'portfolio_return' in store_data and 'ibov_return' in store_data:
            portfolio_return = store_data['portfolio_return']
            ibov_return = store_data['ibov_return']

            fig_ibov.add_trace(go.Scatter(
                x=[item['x'] for item in portfolio_return],
                y=[item['y'] for item in portfolio_return],
                mode='lines',
                name='Portfólio',
                line=dict(
                    color=line_colors.get("portfolio", "#1f77b4"),
                    width=1.2,
                    shape='spline',
                    smoothing=1.0
                ),
                hovertemplate='%{y:.2%}<br>%{x|%d-%m-%Y}'
            ))

            fig_ibov.add_trace(go.Scatter(
                x=[item['x'] for item in ibov_return],
                y=[item['y'] for item in ibov_return],
                mode='lines',
                name='IBOV',
                line=dict(
                    color=line_colors.get("ibov", "#ff7f0e"),
                    width=1.2,
                    shape='spline',
                    smoothing=1.3
                ),
                hovertemplate='%{y:.2%}<br>%{x|%d-%m-%Y}'
            ))

            fig_ibov.update_layout(
                title=dict(
                    text='Retorno Acumulado',
                    x=0.02,
                    xanchor='left',
                    y=0.98,
                    yanchor='top',
                    font=dict(size=12, family="Helvetica")
                ),
                yaxis_title='Retorno (%)',
                hovermode='x',
                hoverlabel=dict(
                    bgcolor="#2c2c2c" if theme == "dark" else "#FFFFFF",
                    font=dict(color="#FFFFFF" if theme == "dark" else "#212529", size=10, family="Helvetica"),
                    bordercolor="rgba(0,0,0,0)"
                ),
                **theme_config
            )

        # Gráfico Retornos Individuais
        fig_individual = go.Figure()
        if 'individual_returns' in store_data and 'tickers' in store_data:
            individual_returns = store_data['individual_returns']
            tickers = store_data['tickers']

            for i, ticker in enumerate(tickers):
                if ticker in individual_returns:
                    fig_individual.add_trace(go.Scatter(
                        x=[item['x'] for item in individual_returns[ticker]],
                        y=[item['y'] for item in individual_returns[ticker]],
                        mode='lines',
                        name=ticker.replace('.SA', ''),
                        line=dict(
                            color=color_sequence[i % len(color_sequence)] if color_sequence else None,
                            width=1.2,
                            shape='spline',
                            smoothing=1.3
                        ),
                        hovertemplate='%{y:.2%}<br>%{x|%d-%m-%Y}'
                    ))

            fig_individual.update_layout(
                title=dict(
                    text='Retorno Acumulado: Tickers Individuais',
                    x=0.02,
                    xanchor='left',
                    y=0.98,
                    yanchor='top',
                    font=dict(size=12, family="Helvetica")
                ),
                yaxis_title='Retorno (%)',
                hovermode='x',
                hoverlabel=dict(
                    bgcolor="#2c2c2c" if theme == "dark" else "#FFFFFF",
                    font=dict(color="#FFFFFF" if theme == "dark" else "#212529", size=10, family="Helvetica"),
                    bordercolor="rgba(0,0,0,0)"
                ),
                **theme_config
            )

        return fig_ibov, fig_individual, False, False

    
    @dash_app.callback(
        Output('stacked-area-chart', 'figure'),
        Output('loading-overlay-area-chart', 'visible'),
        Input('data-store', 'data'),
        Input('theme-store', 'data'),
        prevent_initial_call=False
    )
    @log_callback("update_stacked_area_chart")
    def update_stacked_area_chart(store_data, theme):
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'portfolio_values' not in store_data:
            return go.Figure(), False

        portfolio_values = pd.DataFrame(store_data['portfolio_values'])
        tickers = store_data['tickers']

        # Obtém configurações de tema
        theme_config = get_figure_theme(theme)
        color_sequence = theme_config.pop("color_sequence")
        theme_config.pop("line_colors", None)


        fig = go.Figure()
        for i, ticker in enumerate(tickers):
            if ticker in portfolio_values.columns:
                fig.add_trace(go.Scatter(
                    x=portfolio_values.index,
                    y=portfolio_values[ticker],
                    mode='lines',
                    name=ticker.replace('.SA', ''),
                    stackgroup='one',
                    line=dict(width=0),
                    fillcolor=color_sequence[i % len(color_sequence)],
                    opacity=0.7,
                    hovertemplate='%{y:.2f} R$<br>%{x|%d-%m-%Y}<br>' + ticker.replace('.SA', '')
                ))

        fig.update_layout(
            title=dict(
                text='Composição do Portfólio: Área Empilhada',
                x=0.02,
                xanchor='left',
                y=0.98,
                yanchor='top',
                font=dict(size=12, family="Helvetica")
            ),
            yaxis_title='Valor (R$)',
            hovermode='closest',
            hoverlabel=dict(
                bgcolor="#2c2c2c" if theme == "dark" else "#FFFFFF",
                font=dict(color="#FFFFFF" if theme == "dark" else "#212529", size=10, family="Helvetica"),
                bordercolor="rgba(0,0,0,0)"
            ),
            #transition=dict(duration=100, easing='cubic-in-out'),
            showlegend=True,
            **theme_config          
        )
        fig.update_traces(
            hovertemplate='<b>%{fullData.name}</b><br>x: %{x}<br>y: %{y}<extra></extra>'
        )
        return fig, False