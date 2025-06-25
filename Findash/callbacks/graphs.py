from dash import Dash, Output, Input
import plotly.graph_objects as go
from utils.serialization import orjson_loads
from Findash.utils.plot_style import get_figure_theme

def register_graph_callbacks(dash_app: Dash):
    """
    Registra callbacks relacionados a gráficos no Dash app.
    
    Args:
        dash_app (Dash): Instância do aplicativo Dash.
    """
    @dash_app.callback(
        Output('portfolio-ibov-line', 'figure'),
        Input('data-store', 'data'),
        Input('theme-store', 'data'),
        prevent_initial_call=False
    )
    def update_portfolio_ibov_line(store_data, theme):
        """
        Atualiza o gráfico de linha comparando o retorno acumulado do portfólio e do IBOV.
        """
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'portfolio_return' not in store_data or 'ibov_return' not in store_data:
            return go.Figure()

        portfolio_return = store_data['portfolio_return']
        ibov_return = store_data['ibov_return']

        # Obtém configurações de tema e separa as cores de linha
        theme_config = get_figure_theme(theme)
        line_colors = theme_config.pop("line_colors")
        theme_config.pop("color_sequence", None)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=list(portfolio_return.keys()),
            y=list(portfolio_return.values()),
            mode='lines',
            name='Portfólio',
            line=dict(
                color=line_colors["portfolio"], 
                width=1.2, 
                shape='spline', 
                smoothing=1.3
            ),
            hovertemplate='%{y:.2%}<br>%{x|%d-%m-%Y}'
        ))
       
        fig.add_trace(go.Scatter(
            x=list(ibov_return.keys()),
            y=list(ibov_return.values()),
            mode='lines',
            name='IBOV',
            line=dict(color=line_colors["ibov"], width=1.2, shape='spline', smoothing=1.3),
            hovertemplate='%{y:.2%}<br>%{x|%d-%m-%Y}'
        ))

        fig.update_layout(
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
            transition=dict(duration=100, easing='cubic-in-out'),
            **theme_config 
        )

        return fig
    # Retorno acumulado:tickers individuais
    @dash_app.callback(
        Output('individual-tickers-line', 'figure'),
        Input('data-store', 'data'),
        Input('theme-store', 'data'),
        prevent_initial_call=False
    )
    def update_individual_tickers_line(store_data, theme):

        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'individual_returns' not in store_data:
            return go.Figure()

        individual_returns = store_data['individual_returns']
        tickers = store_data['tickers']

        # Obtém configurações de tema
        theme_config = get_figure_theme(theme)
        color_sequence = theme_config.pop("color_sequence")
        theme_config.pop("line_colors", None) # Remove line_colors

        fig = go.Figure()
        for i, ticker in enumerate(tickers):
            if ticker in individual_returns:
                fig.add_trace(go.Scatter(
                    x=list(individual_returns[ticker].keys()),
                    y=list(individual_returns[ticker].values()),
                    mode='lines',
                    name=ticker.replace('.SA', ''),
                    line=dict(
                        color= color_sequence[i % len(color_sequence)],
                        width=1.2,
                        shape='spline',
                        smoothing=1.3
                    ),
                    hovertemplate='%{y:.2%}<br>%{x|%d-%m-%Y}'
                ))

        fig.update_layout(
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
            transition=dict(duration=100, easing='cubic-in-out'),
            **theme_config
        )
        return fig