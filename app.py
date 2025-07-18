from flask import Flask, Response, session, redirect, url_for, render_template, request, jsonify, make_response, Response, flash
from flask_session import Session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from redis.exceptions import RedisError, ConnectionError
from typing import Optional, Dict
import redis
import os
import re
import logging
import sqlite3
from uuid import uuid4
from datetime import timedelta, datetime
from Findash.app_dash import init_dash
from Findash.services.portfolio_services import PortfolioService
from utils.serialization import orjson_dumps, orjson_loads
from werkzeug.security import generate_password_hash, check_password_hash
from Segurai.app_dash import init_segurai_dash

from Segurai.services.model_handler import carregar_modelos, prever_todos_modelos
from Segurai.utils.encoder import preparar_dados_entrada # encoder e função para montar X_input

# Constantes para cache de empresas
TICKER_CACHE_PREFIX = "ticker_data:"
CACHE_EXPIRATION_SECONDS = 24 * 60 * 60  # 24 horas
DATABASE_PATH = "Findash/data/tickers.db"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

def create_app():
    app = Flask(__name__, 
                static_folder='static', 
                static_url_path='/static')
    app.secret_key = os.getenv('SECRET_KEY', '123456')
    

    # Configuração da sessão Session Flask + Redis (DB0)
    app.config.update(
        SESSION_TYPE='redis',
        SESSION_REDIS=redis.Redis(host='localhost', port=6379, db=0),  # Sessões no Redis DB 0
        SESSION_COOKIE_NAME='synapsi_session',
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=(os.getenv('FLASK_ENV') == 'production'),
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        SESSION_KEY_PREFIX='session:'
    )
    Session(app)

    # Redis separado para dados do portfólio (DB1)
    data_redis = redis.Redis(host='localhost', port=6379, db=1)
    # Redis para dados das empresas (DB3)
    empresas_redis = redis.Redis(host='localhost', port=6379, db=3)

    
    # Redis para dados do SegurAI (não sessões)
    segurai_redis = redis.Redis(host='localhost', port=6379, db=2)

    try:
        app.config['SESSION_REDIS'].ping()
        data_redis.ping()
        empresas_redis.ping()
        logger.info("Redis de sessão DB0 e dados conectados DB1, DB3.")
    except ConnectionError as e:
        logger.error(f"Erro ao conectar no Redis: {str(e)}")
        raise RuntimeError("Redis não está disponível.")

    # Middleware: tratamento de sessão e criação de user_id
    @app.before_request
    def ensure_user_id():
        """
        Garante que cada visitante (autenticado ou anônimo) tenha um 'user_id' único
        salvo na sessão Flask para identificação consistente.
        """
        # Ignora arquivos estáticos
        if request.path.startswith('/static/'):
            return

        try:
            # Garante que a sessão esteja acessível
            _ = session._get_current_object()
        except Exception as e:
            # Tratamento de sessão corrompida
            logger.error(f"Sessão corrompida: {e}. Limpando e redirecionando.")
            session.clear()
            response = make_response(redirect(request.url))
            response.set_cookie(app.config['SESSION_COOKIE_NAME'], '', expires=0)
            return response

        if current_user.is_authenticated:
            # Usuário autenticado: usar ID real
            session['user_id'] = current_user.id
            logger.debug(f"Usuário autenticado detectado | user_id={session['user_id']}")
        else:
            # Usuário anônimo: criar UUID se não existir
            if 'user_id' not in session:
                session['user_id'] = str(uuid4())
                logger.info(f"Novo user_id anônimo criado: {session['user_id']}")
            else:
                logger.debug(f"Usuário anônimo com user_id existente: {session['user_id']}")

        session.modified = True
        session.permanent = True  # aplica tempo de expiração

    # Iniciar Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    # Serviço de portfólio (com redis de dados)
    portfolio_service = PortfolioService()
    portfolio_service.redis_client = data_redis

    @login_manager.user_loader
    def load_user(user_id):
        # Aqui você deve consultar o banco de dados para obter o usuário
        # Por enquanto, mock simples
        return User(user_id) if portfolio_service.db.get_user_by_id(user_id) else None
    
    class User(UserMixin):
        def __init__(self, id):
            self.id = id

    # Inicializar apps
    dash_app = init_dash(app, portfolio_service)
    segurai_dash = init_segurai_dash(app)

    # Lista estática de tickers (mantida por enquanto)
    TICKERS = [
        {"symbol": "PETR4.SA", "name": "Petrobras PN"},
        {"symbol": "VALE3.SA", "name": "Vale ON"},
        {"symbol": "ITUB4.SA", "name": "Itaú Unibanco PN"},
        {"symbol": "BBDC4.SA", "name": "Bradesco PN"},
        {"symbol": "ABEV3.SA", "name": "Ambev ON"},
        {"symbol": "CSAN3.SA", "name": "Cosan ON"},
        {"symbol": "PRIO3.SA", "name": "PetroRio ON"},
        {"symbol": "UGPA3.SA", "name": "Ultrapar ON"},
        {"symbol": "VBBR3.SA", "name": "Vibra Energia ON"},
        {"symbol": "BRAP4.SA", "name": "Bradespar PN"},
        {"symbol": "CSNA3.SA", "name": "CSN ON"},
        {"symbol": "GGBR4.SA", "name": "Gerdau PN"},
        {"symbol": "USIM5.SA", "name": "Usiminas PNA"},
        {"symbol": "BRKM5.SA", "name": "Braskem PNA"},
        {"symbol": "SUZB3.SA", "name": "Suzano ON"},
        {"symbol": "EMBR3.SA", "name": "Embraer ON"},
        {"symbol": "WEGE3.SA", "name": "WEG ON"},
        {"symbol": "RAIL3.SA", "name": "Rumo ON"},
        {"symbol": "CCRO3.SA", "name": "CCR ON"},
        {"symbol": "ECOR3.SA", "name": "Ecorodovias ON"},
        {"symbol": "BRFS3.SA", "name": "BRF ON"},
        {"symbol": "JBSS3.SA", "name": "JBS ON"},
        {"symbol": "MRFG3.SA", "name": "Marfrig ON"},
        {"symbol": "BEEF3.SA", "name": "Minerva ON"},
        {"symbol": "SMTO3.SA", "name": "São Martinho ON"},
        {"symbol": "MGLU3.SA", "name": "Magazine Luiza ON"},
        {"symbol": "LREN3.SA", "name": "Lojas Renner ON"},
        {"symbol": "BHIA3.SA", "name": "Casas Bahia ON"},
        {"symbol": "MRVE3.SA", "name": "MRV ON"},
        {"symbol": "CYRE3.SA", "name": "Cyrela ON"},
    ]

    
    # -------------------------------
    # ROTAS PRINCIPAIS
    # -------------------------------
    
    def get_portfolio_for_session_user() -> Optional[Dict]:
        """
        Retorna o portfólio associado ao usuário atual da sessão.
        - Se o usuário for autenticado, tenta carregar do banco.
        - Caso contrário, tenta carregar do Redis usando o user_id da sessão.

        Returns:
            dict com os dados do portfólio, ou None se não encontrado.
        """
        user_id = session.get('user_id')
        
        if not user_id:
            logger.warning("get_portfolio_for_session_user chamado sem user_id na sessão.")
            return None

        if current_user.is_authenticated:
            logger.info(f"[PORTFÓLIO] Usuário autenticado → carregando do banco | user_id={user_id}")
            return portfolio_service.load_portfolio(user_id)

        logger.info(f"[PORTFÓLIO] Usuário anônimo → carregando do Redis | user_id={user_id}")
        raw_data = data_redis.get(f"portfolio:{user_id}")
        return orjson_loads(raw_data) if raw_data else None

    def get_ticker_data(ticker:str) -> Optional[Dict]:
        """Obtém dados da empresa do Redis (DB3) ou tickers.db, cacheando se necessário."""
        chache_key = f"{TICKER_CACHE_PREFIX}{ticker}"
        try:
            # Verificar Cache
            cached_data = empresas_redis.get(chache_key)
            if cached_data:
                logger.debug(f"Dados do ticker {ticker} obtidos do cache Redis (DB3).")
                return orjson_loads(cached_data)
            
            # Consultar Banco
            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ticker, nome, inicio_negociacao, cnpj, sobre,
                    setor_economico, subsetor, segmento, site
                FROM empresas WHERE ticker = ?
            """, (ticker,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                logger.warning(f"Ticker {ticker} não encontrado em tickers.db.")
                return None
            data = {
                "ticker": row["ticker"],
                "nome": row["nome"],
                "inicio_negociacao": row["inicio_negociacao"],
                "cnpj": row["cnpj"],
                "sobre": row["sobre"],
                "setor_economico": row["setor_economico"],
                "subsetor": row["subsetor"],
                "segmento": row["segmento"],
                "site": row["site"]
            }
            # Cachear resultado
            empresas_redis.setex(
                chache_key,
                CACHE_EXPIRATION_SECONDS,
                orjson_dumps(data)
            )
            logger.info(f"Dados do ticker {ticker} consultados em tickers.db e cacheados em Redis (DB3).")
            return data
        except Exception as e:
            logger.error(f"Erro ao obter dados do ticker {ticker}: {str(e)}")
            return None
    
    @app.route('/')
    def homepage():
        return render_template('homepage.html') 

    @app.route('/findash')
    def findash_home():
        try:
            logger.info(f"Acessando /findash | user_id={session.get('user_id')}")
            return render_template('findash_home.html')  # Ex: botão para entrar no Dash
        except RedisError as e:
            logger.error(f"Erro no Redis ao acessar /findash | user_id={session.get('user_id')}: {str(e)}")
            return render_template('findash_home.html', error="Erro ao carregar a página.")
   
    @app.route('/get-tickers', methods=['GET'])
    def get_tickers():
        """Retorna a lista de tickers disponíveis a partir do banco de dados."""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT ticker, nome FROM empresas ORDER BY ticker")
            rows = cursor.fetchall()
            tickers = [{"symbol": row["ticker"], "name": row["nome"]} for row in rows]
            conn.close()

            return Response(
                orjson_dumps(tickers),
                mimetype='application/json'
            )
        except Exception as e:
            return Response(
                orjson_dumps({"erro": str(e)}),
                mimetype='application/json',
                status=500
            )
        
    @app.route('/dashboard', methods=['POST'])
    def dashboard():
        logger.info("/dashboard | Recebendo dados do formulário para criação de portfólio em dash_entry/")
        user_id = session.get('user_id')
        
        # Definindo o plano do usuário
        if not current_user.is_authenticated:
            session['is_registered'] = False
            session['plan_type'] = 'free'
            session['tickers_limit'] = 5
            logger.info(f"Usuário anônimo | user_id={user_id}")
        else:
            logger.info(f"Usuário autenticado | user_id={user_id}")

        try:
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            tickers = request.form.getlist('tickers[]')
            quantities = request.form.getlist('quantities[]')

            logger.info(f"Dados recebidos | user_id={user_id} | tickers={tickers} | quantities={quantities} | start_date={start_date} | end_date={end_date}")

            if not all([tickers, quantities, start_date, end_date]):
                logger.error(f"Dados incompletos | user_id={user_id}")
                raise ValueError("Todos os campos (tickers, quantidades, start_date, end_date) são obrigatórios")
                        
            quantities = [int(q) for q in quantities]

            # Cachear dados dos tickers selecionados
            for ticker in tickers:
                ticker_data = get_ticker_data(ticker)
                if not ticker_data:
                    logger.error(f"Ticker {ticker} inválido | user_id={user_id}")
                    raise ValueError(f"Ticker {ticker} não encontrado.")
                                        
            essencials = {
                'tickers': tickers,
                'quantities': quantities,
                'start_date': start_date,
                'end_date': end_date,
            }
            session['initial_portfolio_essentials'] = orjson_dumps(essencials).decode('utf-8')
            session.modified = True

            return redirect(url_for('dash_entry'))
       
        except Exception as e:
            logger.error(f"Erro ao processar formulário de portfólio | user_id={user_id}: {e}")
            return render_template(
                'findash_home.html',
                end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                error=str(e)
            )

    @app.route('/dash_entry', methods=['GET'])
    def dash_entry():
        user_id = session.get('user_id')
        try:
            # Tenta criar o portfólio com base nos dados da sessão
            essentials_raw = session.pop('initial_portfolio_essentials', None)
            if essentials_raw:
                essentials = orjson_loads(essentials_raw)
                portfolio = portfolio_service.create_portfolio(
                    user_id=user_id,
                    tickers=essentials['tickers'],
                    quantities=essentials['quantities'],
                    start_date=essentials['start_date'],
                    end_date=essentials['end_date'],
                    is_registered=session.get('is_registered', False),
                    tickers_limit=session.get('tickers_limit', 5),
                    plan_type=session.get('plan_type', 'free')
                )
                logger.info(f"Portfólio criado com base nos dados essenciais | user_id={user_id}")

                # Salvar portfólio completo no Redis (para uso no Dash)
                data_redis.setex(f"portfolio:{user_id}", 1800, orjson_dumps(portfolio))
                logger.info(f"Portfólio completo salvo no Redis | user_id={user_id}")

                # Se usuário autenticado, salva os dados essenciais no banco
                if current_user.is_authenticated:
                    portfolio_service.save_portfolio(user_id, portfolio)
                    logger.info(f"Dados essenciais salvos no banco | user_id={user_id}")
            else:
                # Caso não haja dados na sessão, tenta carregar de fontes persistentes
                portfolio = get_portfolio_for_session_user()
                if not portfolio:
                     flash("Nenhum portfólio encontrado. Crie um novo.", "warning")
                     return redirect(url_for('findash_home'))
                
            # Anexa metadados de controle (plano) ao portfólio
            portfolio.update({
                'is_registered': session.get('is_registered', False),
                'plan_type': session.get('plan_type', 'free'),
                'tickers_limit': session.get('tickers_limit', 5)
            })

            # Serializar com orjson e salvar na sessão
            session['initial_portfolio'] = orjson_dumps(portfolio).decode('utf-8')
            session.modified = True
            logger.info(f"Portfólio salvo na sessão para Dash | user_id={user_id} | tickers={portfolio['tickers']}")

            return dash_app.index()
        
        except Exception as e:
            logger.error(f"Erro ao carregar /dash_entry | user_id={user_id}: {str(e)}")
            flash("Erro ao carregar o portfólio. Tente novamente.", "danger")
            return redirect(url_for('findash_home'))

    @app.route('/get-ticker-data/<ticker>', methods=['GET'])
    def get_ticker_data_endpoint(ticker):
        """Retorna dados da empresa para o ticker especificado, usando cache."""
        try:
            data = get_ticker_data(ticker)
            if not data:
                return Response(
                    orjson_dumps({"erro": f"Ticker {ticker} não encontrado"}),
                    mimetype='application/json',
                    status=404
                )
            return Response(
                orjson_dumps(data),
                mimetype='application/json'
            )
        except Exception as e:
            logger.error(f"Erro ao obter dados do ticker {ticker}: {str(e)}")
        return Response(
            orjson_dumps({"erro": str(e)}),
            mimetype='application/json',
            status=500
        )


    @app.route('/logout')
    def logout():
        logger.info(f"Logout solicitado | user_id={session.get('user_id')}")
        logout_user()
        session.clear()
        session['user_id'] = str(uuid4())  # Novo ID para sessão
        response = redirect(url_for('homepage'))
        response.set_cookie(app.config['SESSION_COOKIE_NAME'], '', expires=0)
        return response
    
    def set_user_session(user_id, plan_type='free'):
        session['user_id'] = user_id
        session['is_registered'] = (plan_type == 'registered')
        session['plan_type'] = plan_type
        session['tickers_limit'] = 8 if plan_type == 'registered' else 5
        session.permanent = True

    @app.route('/signup', methods=['POST'])
    def signup():

        email = request.form.get('email')
        password = request.form.get('password')

        # Validação de campos
        if not email or not password:
            flash("Email e senha são obrigatórios.", "danger")
            return redirect(url_for('findash_home'))

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            flash("Formato de email inválido.", "danger")
            return redirect(url_for('findash_home'))

        if len(password) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for('findash_home'))

        try:
            user_id = str(uuid4())
            password_hash = generate_password_hash(password)
            portfolio_service.db.add_user(user_id, email, password_hash)
            portfolio_service.db.add_plan(user_id, plan_type="registered")

            login_user(User(user_id))
            set_user_session(user_id, plan_type='registered')

            logger.info(f"Usuário cadastrado com sucesso: {email} | id={user_id}")
            flash("Cadastro realizado com sucesso! Crie seu portfólio com até 8 tickers.", "success")
            return redirect(url_for('findash_home'))

        except ValueError as e:
            logger.error(f"Erro no cadastro: {str(e)}")
            flash(str(e), "danger")
            return redirect(url_for('findash_home'))
    
    @app.route('/login', methods=['POST'])
    def login():
        email = request.form.get('email')
        password = request.form.get('password')
        logger.info(f"Tentativa de login | email={email}")

        if not email or not password:
            flash("Email e senha são obrigatórios.", "danger")
            return redirect(url_for('findash_home'))

        user = portfolio_service.db.get_user_by_email(email)
        if not user or not check_password_hash(user['password_hash'], password):
            flash("Email ou senha inválidos.", "danger")
            return redirect(url_for('findash_home'))

        user_id = user['id']
        login_user(User(user_id))

        try:
            # Carregar plano
            plan = portfolio_service.db.get_plan_by_user_id(user_id)
            if not plan:
                raise ValueError("Plano do usuário não encontrado.")

            # Atualizar sessão
            set_user_session(user_id, plan_type=plan['plan_type'])

            # Carregar portfólio salvo
            portfolio = portfolio_service.load_portfolio(
                user_id=user_id,
                is_registered=True,
                tickers_limit=session.get('tickers_limit', 8),
                plan_type=session.get('plan_type', 'registered')
                )
            if portfolio:
                flash("Portfólio carregado automaticamente.", "success")
                return redirect(url_for('dash_entry'))

            flash("Bem-vindo! Crie seu portfólio com até 8 tickers.", "success")
            return redirect(url_for('findash_home'))

        except Exception as e:
            logger.error(f"Erro durante login ou carregamento de dados | user_id={user_id}: {e}")
            flash("Erro ao carregar informações do usuário. Crie um novo portfólio.", "warning")
            return redirect(url_for('findash_home'))

    @app.route('/redis-test')
    def redis_test():
        try:
            user_id = session.get('user_id')
            portfolio_key = f"portfolio:{user_id}"

            # Testa Redis de dados
            portfolio_service.redis_client.set(portfolio_key, orjson_dumps({'test': 'ok'}))
            result = portfolio_service.redis_client.get(portfolio_key)
            decoded = orjson_loads(result)

            # Testa Redis de sessão
            flask_session_keys = app.config['SESSION_REDIS'].keys('session:*')

            return jsonify({
                'status': 'ok',
                'portfolio_key': portfolio_key,
                'portfolio_value': decoded,
                'session_keys': [key.decode('utf-8') for key in flask_session_keys]
            })
        except RedisError as e:
            return jsonify({'status': 'erro', 'mensagem': str(e)}), 500
        

    @app.route('/blog', methods=['GET'])
    def blog():
        """Placeholder para a página de blog."""
        return render_template('blog.html')

    @app.route('/company', methods=['GET'])
    def company():
        """Placeholder para a página da empresa."""
        return render_template('company.html')
    
    @app.route('/segurai', methods=['GET'])
    def segurai():
        """Renderiza a página do Segurai."""
        return render_template('segurai.html')    
    
    @app.route('/dashboard_segurai', methods=['POST'])

    def dashboard_segurai():
        idade = int(request.form.get('idade'))
        renda = int(request.form.get('renda'))
        sinistro = int(request.form.get('sinistro'))
        uf = request.form.get('uf')
        tipo = request.form.get('tipo_seguro')
        estado_civil = request.form.get('estado_civil')

        # Validação básica
        if not all([idade, renda, uf, tipo, estado_civil]):
            return "Dados incompletos", 400
        
        # Monta dicionário com os dados informados
        segurai_data = {
            'idade': idade,
            'renda': renda,
            'sinistro': sinistro,
            'uf': uf,
            'tipo_seguro': tipo,
            'estado_civil': estado_civil
        }

        # Salva na sessão do Redis (db=0) para uso temporário
        session['segurai_data'] = orjson_dumps(segurai_data).decode('utf-8')

        return redirect(url_for('dash_entry_segurai'))

    @app.route('/dash_entry_segurai', methods=['GET'])
    def dash_entry_segurai():
        if 'segurai_data' not in session:
            return redirect(url_for('segurai'))
        
        # Recupera dados do formulário da sessão
        dados_raw = orjson_loads(session['segurai_data'].encode('utf-8'))
        # Prepara o X_input (DataFrame com as mesmas colunas dos modelos)
        X_input = preparar_dados_entrada(dados_raw)
        # Carrega modelos e scaler da Regressão Logística
        modelos, scaler_rl = carregar_modelos()
        # Faz as previsões em todos os modelos (com escala na RL)
        resultados = prever_todos_modelos(X_input, modelos, scaler_rl)
        # Salva os resultados no Redis db=2 (segurai_redis)
        user_id = str(uuid4())
        segurai_redis.set(f'resultado:{user_id}', orjson_dumps({
                'entrada': dados_raw,
                'resultado': resultados
        }))

        # Salva resultado na sessão para uso no Dash
        session['segurai_resultado'] = orjson_dumps({
            'entrada': dados_raw,
            'resultado': resultados
        }).decode('utf-8')

        return segurai_dash.index()
    
    @app.route('/ver-session')
    def ver_session():
        print(session.keys())  # Mostra no console do servidor
        return str(list(session.keys()))  # Retorna as chaves como resposta HTTP

    
    return app

if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(debug=True, use_reloader=True)