from dash import Dash, Output, Input
import plotly.graph_objects as go
from utils.serialization import orjson_loads
from Findash.utils.plot_style import get_figure_theme, get_color_sequence
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
        Output('loading-overlay-ibov', 'visible'),
        Input('data-store', 'data'),
        Input('theme-store', 'data'),
        prevent_initial_call=False
    )
    @log_callback("update_portfolio_vs_ibov_line")
    def update_portfolio_vs_ibov_line(store_data, theme):
        if not store_data:
            return go.Figure(), False

        try:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data
        except orjson.JSONDecodeError:
            logger.error("Erro ao deserializar store_data")
            return go.Figure(), False

        color_sequence = get_color_sequence(theme)

        # === Gráfico: Portfólio vs IBOV ===
        traces_ibov = []
        if 'portfolio_return' in store_data and 'ibov_return' in store_data:
            traces_ibov.append(go.Scatter(
                x=[pt['x'] for pt in store_data['portfolio_return']],
                y=[pt['y'] for pt in store_data['portfolio_return']],
                mode='lines',
                name='Portfólio',
                line=dict(color=color_sequence[0], width=1.2, shape='spline', smoothing=1.0),
                hovertemplate='%{y:.2%}<br>%{x|%d-%m-%Y}'
            ))
            traces_ibov.append(go.Scatter(
                x=[pt['x'] for pt in store_data['ibov_return']],
                y=[pt['y'] for pt in store_data['ibov_return']],
                mode='lines',
                name='IBOV',
                line=dict(color=color_sequence[1], width=1.2, shape='spline', smoothing=1.3),
                hovertemplate='%{y:.2%}<br>%{x|%d-%m-%Y}'
            ))

        fig_ibov = go.Figure(data=traces_ibov)
        fig_ibov.update_layout(**get_figure_theme(theme, title="Retorno Acumulado", yaxis_title="Retorno (%)"))
        return fig_ibov, False
    
    @dash_app.callback(
        Output('individual-tickers-line', 'figure'),
        Output('loading-overlay-individual', 'visible'),
        Input('data-store', 'data'),
        Input('theme-store', 'data'),
        prevent_initial_call=False
    )
    @log_callback("update_individual_tickers_line")
    def update_individual_tickers_line(store_data, theme):
        if not store_data:
            return go.Figure(), False
        try:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data
        except orjson.JSONDecodeError:
            logger.error("Erro ao deserializar store_data")
            return go.Figure(), False

        color_sequence = get_color_sequence(theme)
    
        traces_individual = []
        if 'individual_returns' in store_data and 'tickers' in store_data:
            for i, ticker in enumerate(store_data['tickers']):
                if ticker in store_data['individual_returns']:
                    traces_individual.append(go.Scatter(
                        x=[pt['x'] for pt in store_data['individual_returns'][ticker]],
                        y=[pt['y'] for pt in store_data['individual_returns'][ticker]],
                        mode='lines',
                        name=ticker.replace(".SA", ""),
                        line=dict(
                            color=color_sequence[i % len(color_sequence)],
                            width=1.2,
                            shape='spline',
                            smoothing=1.3
                        ),
                        hovertemplate='%{y:.2%}<br>%{x|%d-%m-%Y}'
                    ))
        fig = go.Figure(data=traces_individual)
        fig.update_layout(**get_figure_theme(theme, title="Retorno Acumulado: Tickers Individuais", yaxis_title="Retorno (%)"))
        
        return fig, False

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
        color_sequence = get_color_sequence(theme)

        traces = []
        for i, ticker in enumerate(tickers):
            if ticker in portfolio_values.columns:
                traces.append(go.Scatter(
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

        fig = go.Figure(data=traces)
        fig.update_layout(**get_figure_theme(theme, title="Composição do Portfólio: Área Empilhada", yaxis_title="Valor (R$)"))
        
        return fig, False
    
    @dash_app.callback(
        Output('portfolio-treemap', 'figure'),
        Input('data-store', 'data'),
        Input('theme-store', 'data'),
        prevent_initial_call=False
    )
    @log_callback("update_portfolio_treemap")
    def update_portfolio_treemap(store_data, theme):

        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data

        if not store_data or 'table_data' not in store_data:
            return go.Figure(go.Treemap())
        
        color_sequence = get_color_sequence(theme)
        table_data = store_data['table_data']
        treemap_data = [row for row in table_data if row['ticker'] != 'Total']
        
        fig = go.Figure(go.Treemap(
            labels=[row['ticker'] for row in treemap_data],
            parents=[""] * len(treemap_data),
            values=[float(row['peso_quantidade_percentual']) for row in treemap_data],
            text=[row['ticker'] for row in treemap_data],
            textinfo="text",
            marker=dict(colors=color_sequence)
        ))

        fig.update_layout(**get_figure_theme(theme, title="Peso por Quantidade"))   
        return fig   
    
    @dash_app.callback(
        Output('financial-treemap', 'figure'),
        Input('data-store', 'data'),
        Input('theme-store', 'data'),
        prevent_initial_call=False
    )
    @log_callback("update_financial_treemap")
    def update_financial_treemap(store_data, theme):
        if store_data:
            store_data = orjson_loads(store_data) if isinstance(store_data, (str, bytes)) else store_data
            
        if not store_data or 'tickers' not in store_data or 'quantities' not in store_data or 'portfolio_values' not in store_data:
            return go.Figure()
      
        tickers = store_data['tickers']
        quantities = store_data['quantities']
        portfolio_values = store_data['portfolio_values']
        color_sequence = get_color_sequence(theme)

        valores_financeiros = []
        for ticker, quantidade in zip(tickers, quantities):
            if ticker in portfolio_values and portfolio_values[ticker]:
                ultimo_valor = list(portfolio_values[ticker].values())[-1]
                valores_financeiros.append(quantidade * ultimo_valor)
            else:
                valores_financeiros.append(0.0)

        total_financeiro = sum(valores_financeiros)
        if total_financeiro > 0:
            pesos_financeiros = [v / total_financeiro * 100 for v in valores_financeiros]

            fig = go.Figure(go.Treemap(
                labels=tickers,
                parents=[""] * len(tickers),
                values=pesos_financeiros,
                text=[f"{p:.2f}%" for p in pesos_financeiros],
                textinfo="label+text",
                marker=dict(colors=color_sequence)
            ))
            fig.update_layout(**get_figure_theme(theme, title="Peso Financeiro"))
            return fig
        
        return go.Figure() 
    
    