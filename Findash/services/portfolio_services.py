from typing import List, Dict, Optional
from datetime import datetime, timedelta
from Findash.modules.metrics import obter_dados, calcular_metricas, get_sector
import pandas as pd

class PortfolioService:
    """
    Serviço para gerenciar portfólios financeiros, incluindo criação, atualização,
    adição/remoção de tickers e cálculos de métricas.
    """
    def __init__(self):
        """
        Inicializa o PortfolioService.
        Futuramente, pode aceitar um cache ou repositório de dados como dependência.
        """
        pass

    def validate_dates(self, start_date: str, end_date: str) -> None:
        """
        Valida se as datas fornecidas são válidas e se start_date < end_date.
        
        Args:
            start_date: Data inicial no formato 'YYYY-MM-DD'.
            end_date: Data final no formato 'YYYY-MM-DD'.
        
        Raises:
            ValueError: Se as datas forem inválidas ou start_date >= end_date.
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt >= end_dt:
                raise ValueError("A data inicial deve ser anterior à data final.")
        except ValueError as e:
            if "strptime" in str(e):
                raise ValueError("Formato de data inválido. Use 'YYYY-MM-DD'.")
            raise

    def validate_tickers_and_quantities(self, tickers: List[str], quantities: List[int]) -> None:
        """
        Valida se tickers e quantidades são válidos.
        
        Args:
            tickers: Lista de tickers.
            quantities: Lista de quantidades correspondentes.
        
        Raises:
            ValueError: Se as listas forem inválidas ou não correspondentes.
        """
        if not tickers or not quantities:
            raise ValueError("Tickers e quantidades não podem estar vazios.")
        if len(tickers) != len(quantities):
            raise ValueError("O número de tickers deve ser igual ao número de quantidades.")
        if any(q < 0 for q in quantities):
            raise ValueError("Quantidades não podem ser negativas.")

    def create_portfolio(
        self,
        tickers: List[str],
        quantities: List[int],
        start_date: str,
        end_date: str,
        include_ibov: bool = True
    ) -> Dict:
        """
        Cria um portfólio com base nos tickers, quantidades e período especificado.
        
        Args:
            tickers: Lista de tickers (ex.: ['PETR4.SA', 'VALE3.SA']).
            quantities: Lista de quantidades correspondentes.
            start_date: Data inicial no formato 'YYYY-MM-DD'.
            end_date: Data final no formato 'YYYY-MM-DD'.
            include_ibov: Se True, inclui dados do IBOV (^BVSP).
        
        Returns:
            Dict: Dados do portfólio, incluindo tickers, quantidades, preços, métricas, etc.
        
        Raises:
            ValueError: Se os parâmetros forem inválidos ou não houver dados.
        """
        # Validar entradas
        self.validate_tickers_and_quantities(tickers, quantities)
        self.validate_dates(start_date, end_date)

        # Obter dados financeiros do yfinance
        data = obter_dados(tickers, start_date, end_date, include_ibov)
        if not data['portfolio']:
            raise ValueError("Nenhum dado válido retornado para os tickers fornecidos.")

        # Calcular métricas financeiras
        metrics = calcular_metricas(
            portfolio=data['portfolio'],
            tickers=tickers,
            quantities=quantities,
            start_date=start_date,
            end_date=end_date,
            ibov=data.get('ibov', {}),
            dividends=data.get('dividends', {})
        )

        # Estruturar o portfólio
        portfolio = {
            'tickers': tickers,
            'quantities': quantities,
            'start_date': start_date,
            'end_date': end_date,
            'portfolio': data['portfolio'],
            'ibov': data['ibov'],
            'dividends': data['dividends'],
            'portfolio_return': metrics['portfolio_return'],
            'ibov_return': metrics['ibov_return'],
            'table_data': metrics['table_data'],
            'portfolio_values': metrics['portfolio_values'],
            'setor_pesos': metrics['setor_pesos'],
            'setor_pesos_financeiros': metrics['setor_pesos_financeiros'],
            'individual_returns': metrics['individual_returns'],
            'individual_daily_returns': metrics['individual_daily_returns'],
            'portfolio_daily_return': metrics['portfolio_daily_return']
        }

        return portfolio

    def update_portfolio_period(
        self,
        portfolio: Dict,
        new_start_date: str,
        new_end_date: str
    ) -> Dict:
        """
        Atualiza o período de análise de um portfólio existente.
        
        Args:
            portfolio: Dicionário com os dados do portfólio atual.
            new_start_date: Nova data inicial no formato 'YYYY-MM-DD'.
            new_end_date: Nova data final no formato 'YYYY-MM-DD'.
        
        Returns:
            Dict: Portfólio atualizado com os novos dados e métricas.
        
        Raises:
            ValueError: Se as datas forem inválidas ou o portfólio for inválido.
        """
        if not portfolio or 'tickers' not in portfolio or 'quantities' not in portfolio:
            raise ValueError("Portfólio inválido ou incompleto.")

        self.validate_dates(new_start_date, new_end_date)

        # Recriar o portfólio com o novo período
        return self.create_portfolio(
            tickers=portfolio['tickers'],
            quantities=portfolio['quantities'],
            start_date=new_start_date,
            end_date=new_end_date,
            include_ibov=True
        )

    def add_ticker(
        self,
        portfolio: Dict,
        ticker: str,
        quantity: int
    ) -> Dict:
        """
        Adiciona um novo ticker ao portfólio existente.
        
        Args:
            portfolio: Dicionário com os dados do portfólio atual.
            ticker: Ticker a ser adicionado (ex.: 'PETR4.SA').
            quantity: Quantidade do ticker.
        
        Returns:
            Dict: Portfólio atualizado com o novo ticker.
        
        Raises:
            ValueError: Se o ticker já existir, a quantidade for inválida ou não houver dados.
        """
        if not portfolio or 'tickers' not in portfolio:
            raise ValueError("Portfólio inválido ou incompleto.")
        if ticker in portfolio['tickers']:
            raise ValueError(f"O ticker {ticker} já está no portfólio.")
        if quantity < 0:
            raise ValueError("A quantidade não pode ser negativa.")

        new_tickers = portfolio['tickers'] + [ticker]
        new_quantities = portfolio['quantities'] + [quantity]

        # Recriar o portfólio com o novo ticker
        return self.create_portfolio(
            tickers=new_tickers,
            quantities=new_quantities,
            start_date=portfolio['start_date'],
            end_date=portfolio['end_date'],
            include_ibov=True
        )

    def remove_ticker(self, portfolio: Dict, ticker: str) -> Dict:
        """
        Remove um ticker do portfólio existente.
        
        Args:
            portfolio: Dicionário com os dados do portfólio atual.
            ticker: Ticker a ser removido (ex.: 'PETR4.SA').
        
        Returns:
            Dict: Portfólio atualizado sem o ticker.
        
        Raises:
            ValueError: Se o ticker não existir ou o portfólio for inválido.
        """
        if not portfolio or 'tickers' not in portfolio:
            raise ValueError("Portfólio inválido ou incompleto.")
        if ticker not in portfolio['tickers']:
            raise ValueError(f"O ticker {ticker} não está no portfólio.")

        index = portfolio['tickers'].index(ticker)
        new_tickers = portfolio['tickers'][:index] + portfolio['tickers'][index+1:]
        new_quantities = portfolio['quantities'][:index] + portfolio['quantities'][index+1:]

        if not new_tickers:
            raise ValueError("O portfólio não pode ficar vazio.")

        # Recriar o portfólio sem o ticker
        return self.create_portfolio(
            tickers=new_tickers,
            quantities=new_quantities,
            start_date=portfolio['start_date'],
            end_date=portfolio['end_date'],
            include_ibov=True
        )
    
    # Mover e ajustare para utilizar na camada de serviço
    def calcular_metricas_mensais_anuais(
    self,
    tickers: List[str],
    quantities: List[int],
    portfolio_values: Dict,
    dividends: Dict,
    start_date: str,
    end_date: str
    ) -> Dict:
        """
        Calcula métricas mensais ou anuais de ganho de capital, dividend yield e retorno total.
        
        Args:
            tickers: Lista de tickers.
            quantities: Lista de quantidades por ticker.
            portfolio_values: Dicionário com valores do portfólio (preços diários por ticker).
            dividends: Dicionário com dividendos por ticker.
            start_date: Data inicial (formato 'YYYY-MM-DD').
            end_date: Data final (formato 'YYYY-MM-DD').
        
        Returns:
            Dict: Dicionário com períodos, ganhos de capital, dividend yields e retornos totais.
        """
        # Converter datas para datetime
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Determinar granularidade (mensal ou anual)
        delta_years = (end - start).days / 365.25
        freq = 'ME' if delta_years <= 2 else 'YE'  # Alterado de 'M' para 'ME' e 'Y' para 'YE'
        date_format = '%Y-%m' if freq == 'ME' else '%Y'

        # Criar DataFrame com preços do portfólio
        portfolio_df = pd.DataFrame()
        for ticker in tickers:
            if ticker in portfolio_values and portfolio_values[ticker]:
                df = pd.DataFrame.from_dict(portfolio_values[ticker], orient='index', columns=[ticker])
                df.index = pd.to_datetime(df.index)
                portfolio_df = portfolio_df.join(df, how='outer') if not portfolio_df.empty else df
        portfolio_df = portfolio_df.ffill().loc[start:end]  # Alterado de fillna(method='ffill') para ffill()

        # Calcular valor total do portfólio (preço * quantidade)
        total_portfolio = pd.DataFrame()
        for ticker, qty in zip(tickers, quantities):
            if ticker in portfolio_df.columns:
                total_portfolio[ticker] = portfolio_df[ticker] * qty
        portfolio_series = total_portfolio.sum(axis=1)

        # Resample para períodos mensais ou anuais
        portfolio_monthly_start = portfolio_series.resample(freq).first()
        portfolio_monthly_end = portfolio_series.resample(freq).last()

        # Calcular ganho de capital para cada período
        capital_gains = []
        for i in range(len(portfolio_monthly_start)):
            start_val = portfolio_monthly_start.iloc[i]
            end_val = portfolio_monthly_end.iloc[i]
            if start_val > 0:  # Evitar divisão por zero
                gain = ((end_val - start_val) / start_val) * 100
            else:
                gain = 0.0
            capital_gains.append(float(gain))

        # Calcular dividend yield
        dividend_yields = []
        periods = [d.strftime(date_format) for d in portfolio_monthly_start.index]
        for i, period in enumerate(periods):
            period_start = portfolio_monthly_start.index[i]
            if i < len(portfolio_monthly_start) - 1:
                period_end = portfolio_monthly_start.index[i + 1]
            else:
                period_end = end

            # Somar dividendos no período
            div_total = 0
            for ticker, qty in zip(tickers, quantities):
                if ticker in dividends:
                    div_series = pd.Series(dividends[ticker])
                    div_series.index = pd.to_datetime(div_series.index)
                    div_series = div_series.loc[period_start:period_end]
                    div_total += div_series.sum() * qty

            # Calcular dividend yield (%)
            start_val = portfolio_monthly_start.iloc[i]
            if start_val > 0:
                dy = (div_total / start_val) * 100
            else:
                dy = 0.0
            dividend_yields.append(float(dy))

        # Calcular retorno total (ganho de capital + dividend yield)
        total_returns = [capital_gains[i] + dividend_yields[i] for i in range(len(capital_gains))]

        return {
            'periods': periods,
            'capital_gains': capital_gains,
            'dividend_yields': dividend_yields,
            'total_returns': total_returns
        }
    
    def calcular_dy_por_setor(
        self,
        tickers: List[str],
        quantities: List[int],
        portfolio_values: Dict,
        dividends: Dict,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        Calcula o Dividend Yield (DY) por setor para cada ano no período especificado.
        Ajusta o DY para anos incompletos, anualizando o valor.

        Args:
            tickers: Lista de tickers.
            quantities: Lista de quantidades por ticker.
            portfolio_values: Dicionário com valores do portfólio (preços diários por ticker).
            dividends: Dicionário com dividendos por ticker.
            start_date: Data inicial (formato 'YYYY-MM-DD').
            end_date: Data final (formato 'YYYY-MM-DD').

        Returns:
            Dict: {
                'years': Lista de anos (ex.: ['2023', '2024', '2025*']),
                'setores': Lista de setores,
                'dy_por_setor_por_ano': Dicionário com DY por setor por ano (ex.: {'Petróleo e Gás': {'2023': 5.2, '2024': 4.8}, ...})
            }
        """
        print("Iniciando cálculo de DY por setor")

        # Converter datas para datetime
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        # Determinar os anos no período (inclusive anos incompletos)
        years = list(range(start.year, end.year + 1))
        years_str = [str(year) for year in years]

        # Verificar se o último ano é incompleto
        if end.year == years[-1] and end.month < 12:
            months_covered = end.month
            years_str[-1] = f"{years[-1]}*"  # Marca ano incompleto com asterisco
        else:
            months_covered = 12

        # Obter setores para todos os tickers usando get_sector
        setores_dict = {ticker: get_sector(ticker) for ticker in tickers}
        setores = sorted(set(setores_dict.values()))
        print(f"Setores identificados: {setores}")

        # Inicializar resultado
        dy_por_setor_por_ano = {setor: {year: 0.0 for year in years_str} for setor in setores}

        # Para cada ano, calcular o DY por setor
        for year_idx, year in enumerate(years):
            year_str = years_str[year_idx]
            print(f"Calculando DY para o ano {year_str}")
            # Definir o período do ano
            year_start = pd.to_datetime(f"{year}-01-01")
            year_end = pd.to_datetime(f"{year}-12-31") if year < end.year else end

            # Calcular o número de meses cobertos no ano
            months_in_year = 12 if year < end.year else end.month

            # Criar DataFrame com preços do portfólio para o ano
            portfolio_df = pd.DataFrame()
            for ticker in tickers:
                if ticker in portfolio_values and portfolio_values[ticker]:
                    df = pd.DataFrame.from_dict(portfolio_values[ticker], orient='index', columns=[ticker])
                    df.index = pd.to_datetime(df.index)
                    portfolio_df = portfolio_df.join(df, how='outer') if not portfolio_df.empty else df
            portfolio_df = portfolio_df.ffill().loc[year_start:year_end]

            # Calcular valor inicial de cada ticker no início do ano
            valor_inicial_por_ticker = {}
            for ticker in tickers:
                if ticker in portfolio_df.columns:
                    first_date = portfolio_df.index[portfolio_df.index >= year_start][0]
                    valor_inicial_por_ticker[ticker] = portfolio_df[ticker].loc[first_date]
                else:
                    valor_inicial_por_ticker[ticker] = 0.0

            # Calcular dividendos por setor no ano
            for setor in setores:
                div_total_setor = 0.0
                valor_total_setor = 0.0

                for ticker, qty in zip(tickers, quantities):
                    if setores_dict.get(ticker) != setor:
                        continue

                    # Calcular valor inicial do ticker no setor
                    valor_inicial = valor_inicial_por_ticker.get(ticker, 0.0) * qty
                    valor_total_setor += valor_inicial

                    # Somar dividendos no ano
                    if ticker in dividends:
                        div_series = pd.Series(dividends[ticker])
                        div_series.index = pd.to_datetime(div_series.index)
                        div_series = div_series.loc[year_start:year_end]
                        div_total_setor += div_series.sum() * qty

                print(f"Setor {setor}, Ano {year_str} - Dividendos Totais: {div_total_setor}, Valor Total: {valor_total_setor}")

                # Calcular DY bruto do setor
                if valor_total_setor > 0:
                    dy = (div_total_setor / valor_total_setor) * 100
                    # Ajustar para ano incompleto (anualizar)
                    if year == years[-1] and months_covered < 12:
                        dy = dy * (12 / months_covered)
                    dy_por_setor_por_ano[setor][year_str] = float(dy)

        print("Cálculo de DY por setor concluído")
        return {
            'years': years_str,
            'setores': setores,
            'dy_por_setor_por_ano': dy_por_setor_por_ano
        }