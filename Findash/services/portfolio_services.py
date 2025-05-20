from typing import List, Dict, Optional
from datetime import datetime, timedelta
from Findash.modules.metrics import obter_dados, calcular_metricas, get_sector
import pandas as pd
import time
import orjson
from flask import session
from Findash.services.database import Database
from Findash.utils.serialization import orjson_dumps, orjson_loads
from uuid import uuid4
import logging
logger = logging.getLogger(__name__)


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
        include_ibov: bool = True,
        save_to_db: bool = True
    ) -> Dict:
        logger.info(f"Iniciando create_portfolio | tickers={tickers}, quantities={quantities}, start_date={start_date}, end_date={end_date}, save_to_db={save_to_db}")
        """
        Cria um portfólio com base nos tickers, quantidades e período especificado.
        
        Args:
            tickers: Lista de tickers (ex.: ['PETR4.SA', 'VALE3.SA']).
            quantities: Lista de quantidades correspondentes.
            start_date: Data inicial no formato 'YYYY-MM-DD'.
            end_date: Data final no formato 'YYYY-MM-DD'.
            include_ibov: Se True, inclui dados do IBOV (^BVSP).
            save_to_db: Se True, salva no SQLite para usuários cadastrados.
        
        Returns:
            Dict: Dados do portfólio, incluindo tickers, quantidades, preços, métricas, etc.
        
        Raises:
            ValueError: Se os parâmetros forem inválidos ou não houver dados.
        """
        # Validar limite de tickers com base no plano
        tickers_limit = session.get('tickers_limit', 5)  # Padrão: 5 para gratuito
        if len(tickers) > tickers_limit:
            logger.error(f"Limite de tickers excedido: {len(tickers)} > {tickers_limit}")
            raise ValueError(f"Limite de tickers excedido: máximo de {tickers_limit} tickers permitido.")
        
        # Validar entradas
        self.validate_tickers_and_quantities(tickers, quantities)
        self.validate_dates(start_date, end_date)

        user_id = session.get('user_id')
        if not user_id:
            logger.error("user_id não encontrado na sessão")
            raise ValueError("user_id não encontrado na sessão.")

        logger.info(f"Criando portfólio para user_id existente: {user_id}")


        # Obter dados financeiros do yfinance
        try:
            data = obter_dados(tickers, start_date, end_date, include_ibov)
            if not data['portfolio']:
                logger.error("Nenhum dado válido retornado para os tickers fornecidos")
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
            logger.debug(f"Portfólio criado: {portfolio}")
            # Salvamento no banco apenas para usuários cadastrados
            if save_to_db and session.get('is_registered', False):
                try:
                    logger.info(f"Salvando portfólio no banco para user_id={user_id}")
                    self.db.add_portfolio(user_id, portfolio)
                except ValueError as e:
                    logger.error(f"Erro ao salvar portfólio no banco para user_id={user_id}: {str(e)}")
                    raise 
                
            return portfolio
    
        except Exception as e:
            logger.error(f"Erro em create_portfolio para user_id={user_id}: {str(e)}")
            raise
    
    def save_portfolio(self, user_id: str, portfolio: Dict, name: Optional[str] = None) -> None:
        """
        Salva ou atualiza o portfólio no SQLite com dados essenciais.

        Args:
            user_id: ID do usuário.
            portfolio: Dicionário com os dados do portfólio.
            name: Nome do portfólio (opcional).

        Raises:
            ValueError: Se o portfólio for inválido ou houver erro no salvamento.
        """
        if isinstance(portfolio, str):
            try:
                portfolio = orjson_loads(portfolio)
            except Exception:
                raise ValueError("Portfólio inválido: recebido como string malformada.")

        if not isinstance(portfolio, dict):
            raise ValueError("Portfólio deve ser um dicionário válido.")
    
        is_registered = session.get('is_registered', False)
        plan_type = session.get('plan_type', 'free')
        if not is_registered or plan_type != 'registered':
            raise ValueError("Salvamento disponível apenas para usuários cadastrados.")
        
        if not portfolio or 'tickers' not in portfolio or 'quantities' not in portfolio:
            raise ValueError("Portfólio inválido ou incompleto.")

        # Garantir que todos os campos essenciais estejam presentes
        essential_portfolio = {
            'tickers': portfolio['tickers'],
            'quantities': portfolio['quantities'],
            'start_date': portfolio.get('start_date', ''),
            'end_date': portfolio.get('end_date', ''),
            'name': name or portfolio.get('name', 'Portfólio 1')
        }

        if self.db.has_active_portfolio(user_id):
            # Atualiza portfólio existente
            self.db.update_portfolio(user_id, essential_portfolio, essential_portfolio['name'])
            logger.info(f"Portfólio atualizado para user_id {user_id} com nome {essential_portfolio['name']}")
        else:
            # Adiciona novo portfólio
            self.db.add_portfolio(user_id, essential_portfolio, essential_portfolio['name'])
            logger.info(f"Portfólio salvo para user_id {user_id} com nome {essential_portfolio['name']}")

    def update_portfolio_period(
        self,
        portfolio: Dict,
        new_start_date: str,
        new_end_date: str
    ) -> Dict:
        """
        Atualiza o período de análise de um portfólio existente.
        """
        if not portfolio or 'tickers' not in portfolio or 'quantities' not in portfolio:
            raise ValueError("Portfólio inválido ou incompleto.")

        self.validate_dates(new_start_date, new_end_date)

        # ALTERAÇÃO: Atualiza apenas as datas e recalcula métricas sem recriar portfólio
        # Motivo: Evita chamar create_portfolio, que pode tentar salvar no SQLite
        # Impacto: Resolve erro de limite e mantém edições na sessão
        portfolio['start_date'] = new_start_date
        portfolio['end_date'] = new_end_date

        # Obter novos dados financeiros
        data = obter_dados(portfolio['tickers'], new_start_date, new_end_date, include_ibov=True)
        if not data['portfolio']:
            raise ValueError("Nenhum dado válido retornado para os tickers fornecidos.")

        # Recalcular métricas
        metrics = calcular_metricas(
            portfolio=data['portfolio'],
            tickers=portfolio['tickers'],
            quantities=portfolio['quantities'],
            start_date=new_start_date,
            end_date=new_end_date,
            ibov=data.get('ibov', {}),
            dividends=data.get('dividends', {}),
            get_sector_func=self.get_setor
        )

        # Atualizar portfólio com novos dados
        portfolio.update({
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
        })

        return portfolio

    def add_ticker(
        self,
        portfolio: Dict,
        ticker: str,
        quantity: int
    ) -> Dict:
        """
        Adiciona um novo ticker ao portfólio existente.
        """
        if not portfolio or 'tickers' not in portfolio:
            raise ValueError("Portfólio inválido ou incompleto.")
        if ticker in portfolio['tickers']:
            raise ValueError(f"O ticker {ticker} já está no portfólio.")
        if quantity < 0:
            raise ValueError("A quantidade não pode ser negativa.")
        
        # Validar limite de tickers com base no plano
        tickers_limit = session.get('tickers_limit', 5)  # Padrão: 5 para gratuito
        if len(portfolio['tickers']) + 1 > tickers_limit:
            raise ValueError(f"Limite de tickers excedido: máximo de {tickers_limit} tickers permitido.")

        # Adiciona ticker diretamente ao portfólio      
        new_tickers = portfolio['tickers'] + [ticker]
        new_quantities = portfolio['quantities'] + [quantity]

        # Obter dados financeiros para o novo ticker
        data = obter_dados(new_tickers, portfolio['start_date'], portfolio['end_date'], include_ibov=True)
        if not data['portfolio']:
            raise ValueError("Nenhum dado válido retornado para os tickers fornecidos.")

        # Recalcular métricas
        metrics = calcular_metricas(
            portfolio=data['portfolio'],
            tickers=new_tickers,
            quantities=new_quantities,
            start_date=portfolio['start_date'],
            end_date=portfolio['end_date'],
            ibov=data.get('ibov', {}),
            dividends=data.get('dividends', {}),
            get_sector_func=self.get_setor
        )

        # Atualizar portfólio
        portfolio.update({
            'tickers': new_tickers,
            'quantities': new_quantities,
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
        })

        return portfolio

    def remove_ticker(self, portfolio: Dict, ticker: str) -> Dict:
        """
        Remove um ticker do portfólio existente.
        """
        if not portfolio or 'tickers' not in portfolio:
            raise ValueError("Portfólio inválido ou incompleto.")
        if ticker not in portfolio['tickers']:
            raise ValueError(f"O ticker {ticker} não está no portfólio.")

        # ALTERAÇÃO: Remove ticker diretamente do portfólio sem recriar
        # Motivo: Evita chamar create_portfolio, que pode tentar salvar no SQLite
        # Impacto: Resolve erro de limite e mantém edições na sessão
        index = portfolio['tickers'].index(ticker)
        new_tickers = portfolio['tickers'][:index] + portfolio['tickers'][index+1:]
        new_quantities = portfolio['quantities'][:index] + portfolio['quantities'][index+1:]

        if not new_tickers:
            raise ValueError("O portfólio não pode ficar vazio.")

        # Obter dados financeiros para os tickers restantes
        data = obter_dados(new_tickers, portfolio['start_date'], portfolio['end_date'], include_ibov=True)
        if not data['portfolio']:
            raise ValueError("Nenhum dado válido retornado para os tickers fornecidos.")

        # Recalcular métricas
        metrics = calcular_metricas(
            portfolio=data['portfolio'],
            tickers=new_tickers,
            quantities=new_quantities,
            start_date=portfolio['start_date'],
            end_date=portfolio['end_date'],
            ibov=data.get('ibov', {}),
            dividends=data.get('dividends', {}),
            get_sector_func=self.get_setor
        )

        # Atualizar portfólio
        portfolio.update({
            'tickers': new_tickers,
            'quantities': new_quantities,
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
        })

        return portfolio
    
    # ALTERAÇÃO: Novo método para carregar e recalcular portfólio
    # Motivo: Recalcula métricas a partir dos dados essenciais armazenados
    # Impacto: Garante que métricas sejam atualizadas ao carregar portfólio
    def load_portfolio(self, user_id: str) -> Optional[Dict]:
        """
        Carrega portfólio ativo do usuário e recalcula métricas.

        Args:
            user_id: ID do usuário.

        Returns:
            Dict: Portfólio completo com métricas recalculadas, ou None se não houver portfólio ativo.
        """
        portfolios = self.db.get_active_portfolios(user_id)
        if not portfolios:
            logger.info(f"Nenhum portfólio ativo encontrado para user_id {user_id}")
            return None
        
        portfolio_data = portfolios[0]['portfolio_data']
        name = portfolios[0]['name']

        logger.debug(f"Tipo de portfolio_data: {type(portfolio_data)}, Conteúdo: {portfolio_data}")

        # Verificar se portfolio_data é um dicionário válido
        if not isinstance(portfolio_data, dict):
            logger.error(f"portfolio_data inválido para user_id {user_id}: esperado dicionário, recebido {type(portfolio_data)}")
            raise ValueError("Estrutura de dados do portfólio inválida.")
        
        # Verificar chaves essenciais
        required_keys = ['tickers', 'quantities', 'start_date', 'end_date']
        missing_keys = [key for key in required_keys if key not in portfolio_data]
        if missing_keys:
            logger.error(f"portfolio_data incompleto para user_id {user_id}: faltam chaves {missing_keys}")
            raise ValueError(f"Dados do portfólio incompletos: faltam {missing_keys}")
        
        # Verificar tipos dos dados
        if not isinstance(portfolio_data['tickers'], list) or not isinstance(portfolio_data['quantities'], list):
            logger.error(f"Tipos inválidos em portfolio_data para user_id {user_id}: tickers={type(portfolio_data['tickers'])}, quantities={type(portfolio_data['quantities'])}")
            raise ValueError("Tickers e quantidades devem ser listas.")
        
        # Recalcular portfólio com base nos dados essenciais
        try:
            portfolio = self.create_portfolio(
                tickers=portfolio_data['tickers'],
                quantities=portfolio_data['quantities'],
                start_date=portfolio_data['start_date'],
                end_date=portfolio_data['end_date'],
                include_ibov=True,
                save_to_db=False
            )
            portfolio['name'] = name
            logger.info(f"Portfólio carregado e recalculado para user_id {user_id}")
            return portfolio
        except ValueError as e:
            logger.error(f"Erro ao recalcular portfólio: {str(e)}")
            raise

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
                portfolio_values: Dicionário com preços diários por ticker.
                dividends: Dicionário com dividendos por ticker.
                start_date: Data inicial (formato 'YYYY-MM-DD').
                end_date: Data final (formato 'YYYY-MM-DD').

            Returns:
                Dict com períodos, ganhos de capital, dividend yields e retornos totais.
            """
            
            start_time = time.time()
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)

            delta_years = (end - start).days / 365.25
            freq = 'ME' if delta_years <= 2 else 'YE'
            date_format = '%Y-%m' if freq == 'ME' else '%Y'

            # Montar DataFrame com preços dos ativos
            portfolio_df = pd.DataFrame()
            for ticker in tickers:
                if ticker in portfolio_values and portfolio_values[ticker]:
                    df = pd.DataFrame.from_dict(portfolio_values[ticker], orient='index', columns=[ticker])
                    df.index = pd.to_datetime(df.index)
                    portfolio_df = pd.concat([portfolio_df, df], axis=1) if not portfolio_df.empty else df
            portfolio_df = portfolio_df.ffill().loc[start:end]

            # Calcular valor total do portfólio (preço x quantidade)
            total_portfolio = portfolio_df.mul(quantities, axis=1)
            portfolio_series = total_portfolio.sum(axis=1)

            # Resample: valores no início e fim de cada período
            portfolio_start = portfolio_series.resample(freq).first()
            portfolio_end = portfolio_series.resample(freq).last()

            # Ganho de capital (%)
            capital_gains = ((portfolio_end - portfolio_start) / portfolio_start.replace(0, float('nan'))) * 100
            capital_gains = capital_gains.fillna(0.0).astype(float).tolist()

            # Períodos no formato apropriado
            periods = [d.strftime(date_format) for d in portfolio_start.index]

            # Processar dividendos em um DataFrame
            div_df = pd.DataFrame()
            for ticker, qty in zip(tickers, quantities):
                if ticker in dividends:
                    div_series = pd.Series(dividends[ticker])
                    div_series.index = pd.to_datetime(div_series.index)
                    div_series = div_series * qty
                    div_df[ticker] = div_series
            div_df = div_df.groupby(div_df.index).sum()

            # Calcular dividend yield por período
            dividend_yields = []
            for i, period in enumerate(periods):
                period_start = portfolio_start.index[i]
                period_end = portfolio_start.index[i + 1] if i < len(portfolio_start) - 1 else end
                div_total = div_df.loc[period_start:period_end].sum().sum() if not div_df.empty else 0.0
                start_val = portfolio_start.iloc[i]
                dy = (div_total / start_val * 100) if start_val > 0 else 0.0
                dividend_yields.append(float(dy))

            # Retorno total
            total_returns = [cg + dy for cg, dy in zip(capital_gains, dividend_yields)]

            print(f"calcular_metricas_mensais_anuais: Tempo de execução = {time.time() - start_time:.4f}s")
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