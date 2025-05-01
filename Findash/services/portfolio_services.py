from typing import List, Dict, Optional
from datetime import datetime, timedelta
from Findash.modules.metrics import obter_dados, calcular_metricas, get_sector
import pandas as pd
import time
import orjson
import zlib
import os
import hashlib
from flask import session
from Findash.services.database import Database
from Findash.utils.serialization import orjson_dumps, orjson_loads
from uuid import uuid4


class PortfolioService:
    """
    Serviço para gerenciar portfólios financeiros, incluindo criação, atualização,
    adição/remoção de tickers e cálculos de métricas.
    """
    def __init__(self):
        """
        Inicializa o PortfolioService com um cache interno para setores.
        Futuramente, pode aceitar um cache ou repositório de dados como dependência.
        """
        self.setores_cache = {}  # Cache interno para setores
        self.db = Database()
        self.redis_client = None
        os.makedirs("Findash/cache", exist_ok=True)

    def get_setor(self, ticker: str) -> str:
        """
        Obtém o setor de um ticker, usando cache interno para evitar chamadas repetidas.
        
        Args:
            ticker: Ticker (ex.: 'PETR4.SA').
        
        Returns:
            str: Nome do setor.
        """
        if ticker not in self.setores_cache:
            self.setores_cache[ticker] = get_sector(ticker)
        return self.setores_cache[ticker]

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

        # Gera ou obtém user_id da sessão
        if 'user_id' not in session:
            session['user_id'] = str(uuid4())
        user_id = session['user_id']
        print(f"USER ID: {user_id}")  # Para depuração

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
            dividends=data.get('dividends', {}),
            get_sector_func=self.get_setor
        )

        # Estruturar o portfólio
        portfolio = {
            'id': str(uuid4()),
            'tickers': tickers,
            'quantities': quantities,
            'start_date': start_date,
            'end_date': end_date,
            'created_at': datetime.now().isoformat(),
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
        # Para usuários não cadastrados, retorna o portfólio
        if 'user_authenticated' not in session:
            return portfolio
        
        # Para usuários cadastrados, verifica limite no SQLite
        try:
            portfolio_data = orjson_dumps(portfolio)
            self.db.add_portfolio(user_id, portfolio_data.decode('utf-8'))
            return portfolio
        except ValueError as e:
            raise ValueError(f"Erro ao criar portfólio: {str(e)}")

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
            Calcula métricas mensais ou anuais de ganho de capital, dividend yield e retorno total,
            usando cache Redis e local.
            
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
            
            user_id = session.sid if 'sid' in session else str(uuid4())

            # Gera chave única para o portfólio
            tickers_str = ":".join(sorted(tickers))
            hash_input = f"{tickers_str}:{start_date}:{end_date}"
            tickers_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            cache_key = f"portfolio:{user_id}:{tickers_hash}:{start_date}:{end_date}"

            # Tenta obter do Redis
            cached_data = self.redis_client.get(cache_key) if self.redis_client else None
            if cached_data:
                return orjson_loads(cached_data)
            
            # Tenta obter do cache local
            cache_file = self.db.get_cache_index(user_id, tickers_hash, start_date, end_date)
            if cache_file:
                with open(cache_file, 'rb') as f:
                    return orjson_loads(zlib.decompress(f.read()))

            # Converter datas para datetime
            start_time = time.time()  # Medir tempo total da função
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            # Determinar granularidade (mensal ou anual)
            delta_years = (end - start).days / 365.25
            freq = 'ME' if delta_years <= 2 else 'YE'
            date_format = '%Y-%m' if freq == 'ME' else '%Y'

            # Criar DataFrame com preços do portfólio
            portfolio_df = pd.DataFrame()  # ALTERAÇÃO: Inicializar fora do loop para clareza
            for ticker in tickers:
                if ticker in portfolio_values and portfolio_values[ticker]:
                    df = pd.DataFrame.from_dict(portfolio_values[ticker], orient='index', columns=[ticker])
                    df.index = pd.to_datetime(df.index)
                    # ALTERAÇÃO: Usar concat em vez de join para maior eficiência
                    portfolio_df = pd.concat([portfolio_df, df], axis=1) if not portfolio_df.empty else df
            portfolio_df = portfolio_df.ffill().loc[start:end]

            # Calcular valor total do portfólio (preço * quantidade)
            # ALTERAÇÃO: Usar multiplicação vetorizada em vez de loop
            total_portfolio = portfolio_df.mul(quantities, axis=1)
            portfolio_series = total_portfolio.sum(axis=1)

            # Resample para períodos mensais ou anuais
            portfolio_monthly_start = portfolio_series.resample(freq).first()
            portfolio_monthly_end = portfolio_series.resample(freq).last()

            # Calcular ganho de capital para cada período
            # ALTERAÇÃO: Usar operação vetorizada para ganhos de capital
            capital_gains = ((portfolio_monthly_end - portfolio_monthly_start) / portfolio_monthly_start.replace(0, float('nan'))) * 100
            capital_gains = capital_gains.fillna(0.0).astype(float).tolist()

            # Calcular dividend yield
            dividend_yields = []
            periods = [d.strftime(date_format) for d in portfolio_monthly_start.index]
            # ALTERAÇÃO: Pré-processar dividendos em um DataFrame para evitar múltiplas conversões
            div_df = pd.DataFrame()
            for ticker, qty in zip(tickers, quantities):
                if ticker in dividends:
                    div_series = pd.Series(dividends[ticker])
                    div_series.index = pd.to_datetime(div_series.index)
                    div_series = div_series * qty
                    div_df[ticker] = div_series
            div_df = div_df.groupby(div_df.index).sum()

            for i, period in enumerate(periods):
                period_start = portfolio_monthly_start.index[i]
                period_end = portfolio_monthly_start.index[i + 1] if i < len(portfolio_monthly_start) - 1 else end
                # ALTERAÇÃO: Usar resample para somar dividendos no período
                div_total = div_df.loc[period_start:period_end].sum().sum() if not div_df.empty else 0.0
                start_val = portfolio_monthly_start.iloc[i]
                dy = (div_total / start_val * 100) if start_val > 0 else 0.0
                dividend_yields.append(float(dy))

            # Calcular retorno total (ganho de capital + dividend yield)
            total_returns = [capital_gains[i] + dividend_yields[i] for i in range(len(capital_gains))]

            # ALTERAÇÃO: Imprimir tempo total da função, no estilo metrics.py
            print(f"calcular_metricas_mensuais_anuais: Tempo de execução = {time.time() - start_time:.4f}s")
            metrics = {
                'periods': periods,
                'capital_gains': capital_gains,
                'dividend_yields': dividend_yields,
                'total_returns': total_returns
            }
            # Salva no Redis
            if self.redis_client: # Verifica se redis_client está disponível
                self.redis_client.setex(cache_key, 24 * 3600, orjson_dumps(metrics)) 

            # Salva no cache local
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")
            os.makedirs(cache_dir, exist_ok=True)  # Criar diretório se não existir
            cache_file = os.path.join(cache_dir, f"{tickers_hash}_{start_date}_{end_date}.bin")
            with open(cache_file, 'wb') as f:
                f.write(zlib.compress(orjson_dumps(metrics)))
            print(f"Cache local salvo: {cache_file}")
            expires_at = (datetime.now() + timedelta(days=1)).isoformat()
            self.db.add_cache_index(user_id, tickers_hash, start_date, end_date, cache_file, expires_at)
        
            return metrics
    
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
                'dy_por_setor_por_ano': Dicionário com DY por setor por ano
            }
        """
        start_time = time.time()  # Medir tempo total da função
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

        # Obter setores usando cache interno
        setores_dict = {ticker: self.get_setor(ticker) for ticker in tickers}
        setores = sorted(set(setores_dict.values()))
        print(f"Setores identificados: {setores}")

        # Inicializar resultado
        dy_por_setor_por_ano = {setor: {year: 0.0 for year in years_str} for setor in setores}

        # ALTERAÇÃO: Pré-processar dividendos em um DataFrame para evitar conversões repetitivas
        div_df = pd.DataFrame()
        for ticker, qty in zip(tickers, quantities):
            if ticker in dividends:
                div_series = pd.Series(dividends[ticker])
                div_series.index = pd.to_datetime(div_series.index)
                div_series = div_series * qty
                div_df[ticker] = div_series
        div_df = div_df.groupby(div_df.index).sum()

        # Para cada ano, calcular o DY por setor
        for year_idx, year in enumerate(years):
            year_str = years_str[year_idx]
            print(f"Calculando DY para o ano {year_str}")
            # Definir o período do ano
            year_start = pd.to_datetime(f"{year}-01-01")
            year_end = pd.to_datetime(f"{year}-12-31") if year < end.year else end

            # Calcular o número de meses cobertos no ano
            months_in_year = 12 if year < end.year else end.month

            # ALTERAÇÃO: Criar DataFrame com preços apenas uma vez por ano
            portfolio_df = pd.DataFrame()
            for ticker in tickers:
                if ticker in portfolio_values and portfolio_values[ticker]:
                    df = pd.DataFrame.from_dict(portfolio_values[ticker], orient='index', columns=[ticker])
                    df.index = pd.to_datetime(df.index)
                    # ALTERAÇÃO: Usar concat em vez de join para maior eficiência
                    portfolio_df = pd.concat([portfolio_df, df], axis=1) if not portfolio_df.empty else df
            portfolio_df = portfolio_df.ffill().loc[year_start:year_end]

            # ALTERAÇÃO: Calcular valor inicial de todos os tickers de uma vez
            first_date = portfolio_df.index[portfolio_df.index >= year_start][0]
            valor_inicial = portfolio_df.loc[first_date].fillna(0.0) * quantities

            # ALTERAÇÃO: Calcular dividendos por ticker no ano usando resample
            div_totals = div_df.loc[year_start:year_end].sum() if not div_df.empty else pd.Series(0.0, index=tickers)

            # ALTERAÇÃO: Agrupar por setor usando pandas para evitar loops
            ticker_data = pd.DataFrame({
                'ticker': tickers,
                'setor': [setores_dict[ticker] for ticker in tickers],
                'valor_inicial': valor_inicial,
                'div_total': [div_totals.get(ticker, 0.0) for ticker in tickers]
            })
            setor_agg = ticker_data.groupby('setor').agg({
                'valor_inicial': 'sum',
                'div_total': 'sum'
            })

            # Calcular DY por setor
            for setor in setores:
                valor_total_setor = setor_agg.loc[setor, 'valor_inicial'] if setor in setor_agg.index else 0.0
                div_total_setor = setor_agg.loc[setor, 'div_total'] if setor in setor_agg.index else 0.0
                print(f"Setor {setor}, Ano {year_str} - Dividendos Totais: {div_total_setor}, Valor Total: {valor_total_setor}")

                if valor_total_setor > 0:
                    dy = (div_total_setor / valor_total_setor) * 100
                    # Ajustar para ano incompleto (anualizar)
                    if year == years[-1] and months_covered < 12:
                        dy = dy * (12 / months_covered)
                    dy_por_setor_por_ano[setor][year_str] = float(dy)

        print("Cálculo de DY por setor concluído")
        print(f"calcular_dy_por_setor: Tempo de execução = {time.time() - start_time:.4f}s")
        return {
            'years': years_str,
            'setores': setores,
            'dy_por_setor_por_ano': dy_por_setor_por_ano
        }