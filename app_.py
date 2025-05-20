# app.py
from flask import Flask, render_template, request, redirect, session, url_for, Response, jsonify, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from Findash.app_dash import init_dash as init_portfolio_dash
from flask_session import Session
from Findash.services.portfolio_services import PortfolioService
from Findash.utils.serialization import orjson_dumps, orjson_loads
import orjson
import redis
from redis.exceptions import RedisError
import os
from uuid import uuid4
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import shutil 

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)
logging.getLogger('yfinance').setLevel(logging.WARNING)
logging.getLogger('sqlitedict').setLevel(logging.WARNING)

# Alteração: Filtro personalizado para suprimir logs de requisições HTTP específicas do Dash
class DashRequestFilter(logging.Filter):
    def filter(self, record):
        # Ignora mensagens de requisições GET/POST para rotas do Dash
        if 'GET /dash' in record.msg or 'POST /dash' in record.msg:
            return False
        return True

werkzeug_logger.addFilter(DashRequestFilter())


def create_app():
    # Inicializar Flask
    flask_app = Flask(__name__)
    flask_app.secret_key = os.getenv('SECRET_KEY', '123456')
    flask_app.config['SESSION_TYPE'] = 'redis'
    flask_app.config['SESSION_REDIS'] = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    flask_app.config['SESSION_COOKIE_NAME'] = 'session'
    flask_app.config['SESSION_COOKIE_PATH'] = '/'
    flask_app.config['SESSION_COOKIE_DOMAIN'] = None
    flask_app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    flask_app.config['SESSION_COOKIE_HTTPONLY'] = True
    flask_app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'  # False para desenvolvimento local (http)
    flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    Session(flask_app)

    # Inicializa o cliente Redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    try:
        redis_client.ping()
        logger.info("Conexão com Redis estabelecida com sucesso")
        redis_client.flushall()
        logger.info("Redis limpo com FLUSHALL")
    except ConnectionError as e:
        logger.error(f"Falha na conexão com Redis: {str(e)}. Certifique-se de que o Redis está rodando.")
        raise RuntimeError("Redis não está acessível. Execute 'redis-server' e tente novamente.")
    
    # Limpar diretório flask_session, se existir
    flask_session_dir = os.path.join(flask_app.instance_path, 'flask_session')
    if os.path.exists(flask_session_dir):
        logger.warning(f"Diretório flask_session encontrado em {flask_session_dir}. Removendo para evitar conflitos.")
        shutil.rmtree(flask_session_dir)

    # Middleware para capturar UnicodeDecodeError e limpar sessões corrompidas
    @flask_app.before_request
    def handle_session_errors():
        if request.path.startswith('/static/'):
            return None  # Bypass para arquivos estáticos
        try:
            session._get_current_object()
            logger.debug(f"Sessão carregada com sucesso, Sessão ID: {session.sid}")
        except UnicodeDecodeError as e:
            logger.error(f"Sessão corrompida detectada: {str(e)}. Limpando sessão e cookie.")
            session.clear()
            session['session_id'] = str(uuid4())
            session.modified = True
            response = make_response(redirect(request.url))
            response.set_cookie('session', '', expires=0)  # Invalida cookie antigo
            return response
        
    # Configuração e inicialização do Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'login'  
    login_manager.init_app(flask_app)
    # Inicializar o serviço
    portfolio_service = PortfolioService()
    portfolio_service.redis_client = redis_client

    @login_manager.user_loader
    def load_user(user_id):
        # Aqui você deve consultar o banco de dados para obter o usuário
        # Por enquanto, mock simples
        return User(user_id) if portfolio_service.db.get_user_by_id(user_id) else None
    
    class User(UserMixin):
        def __init__(self, id):
            self.id = id

    # Orjason
    def default(obj):
        raise TypeError  # Se aparecer algo não serializável, melhor levantar erro logo.

    portfolio_dash = init_portfolio_dash(flask_app, portfolio_service)

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

    @flask_app.route('/', methods=['GET'])
    def homepage():
        return render_template('homepage.html')

    # Rotas Flask
    @flask_app.route('/findash', methods=['GET'])
    def findash_home():
        """Renderiza a página inicial com a data final padrão (ontem)."""
        try:
            if not current_user.is_authenticated:
                if 'session_id' not in session:
                    session['session_id'] = str(uuid4())
                    session.modified = True
                    logger.info(f"Nova sessão criada, Sessão ID: {session.sid}, Session UUID: {session['session_id']}")
            end_date_default = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            return render_template('findash_home.html', end_date_default=end_date_default)
        except RedisError as e:
            logger.error(f"Erro ao acessar Redis em /findash: {str(e)}")
            return render_template('findash_home.html', 
                                 end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                                 error="Erro ao carregar a página. Tente novamente.")

    @flask_app.route('/get-tickers', methods=['GET'])
    def get_tickers():
        """Retorna a lista de tickers disponíveis."""
        return Response(
            orjson_dumps(TICKERS),
            mimetype='application/json'
        )

    @flask_app.route('/dashboard', methods=['POST'])
    def dashboard():
        """
        Processa o formulário de criação de portfólio e redireciona para o dashboard.
        """
        logger.info("Processando criação de portfólio")

        # Log do cookie de sessão para depuração
        session_cookie = request.cookies.get('session', 'Nenhum cookie encontrado')
        logger.info(f"Cookie de sessão recebido: {session_cookie}")

        # Definir sessão para usuários não autenticados
        if not current_user.is_authenticated:
            if 'session_id' not in session:
                session['session_id'] = str(uuid4())
            session['is_registered'] = False
            session['plan_type'] = 'free'
            session['tickers_limit'] = 5
            session.permanent = True
            flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
            logger.info(f"Usuário não autenticado: plano free, limite 5 tickers, Sessão ID: {session.sid}")
        else:
            session.permanent = True
            flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
            logger.info(f"Usuário autenticado: plano {session.get('plan_type')}, limite {session.get('tickers_limit')} tickers")

        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        tickers = request.form.getlist('tickers[]')
        quantities = request.form.getlist('quantities[]')

        try:
            quantities = [int(q) for q in quantities]
            logger.info(f"Portfólio: {len(tickers)} tickers, período {start_date} a {end_date}")

            # Criar o portfólio apenas na sessão
            portfolio = portfolio_service.create_portfolio(
                tickers=tickers,
                quantities=quantities,
                start_date=start_date,
                end_date=end_date,
                save_to_db=False
            )
            logger.info("Portfólio criado com sucesso")

            # Armazenar portfólio na sessão com Redis
            if not current_user.is_authenticated:
                session_id = session['session_id']
                redis_client.setex(
                    f"portfolio:{session_id}",
                    1800,  # Expira em 30 minutos
                    orjson_dumps(portfolio)
                )
                session['user_id'] = str(uuid4())
                logger.info(f"Portfólio armazenado no Redis para session_id: {session_id}, user_id: {session['user_id']}")
                redis_keys = redis_client.keys('session:*')
                logger.debug(f"Chaves de sessão no Redis: {redis_keys}")
            else:
                portfolio_service.save_portfolio(current_user.id, portfolio)
                # Portfólios de usuários autenticados são salvos no banco
                logger.info(f"Portfólio salvo no banco para user_id: {current_user.id}")
            
            response = redirect(url_for('dash_entry'))
            return response
        
        except ValueError as e:
            end_date_default = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            logger.error(f"Erro ao criar portfólio: {str(e)}")
            return render_template('findash_home.html', 
                                end_date_default=end_date_default,
                                error=str(e))
        except RedisError as e:
            # Adicionado tratamento de erro para falhas do Redis
            logger.error(f"Erro ao acessar Redis em /dashboard: {str(e)}")
            return render_template('findash_home.html', 
                                 end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                                 error="Erro ao salvar o portfólio. Tente novamente.")
            
    # Rota para testar conexão com Redis
    @flask_app.route('/redis-test', methods=['GET'])
    def redis_test():
        try:
            """Testa a conexão com o Redis usando set e get."""
            test_key = 'test_key'
            test_value = 'Redis OK'
            redis_client.set(test_key, test_value)
            result = redis_client.get(test_key)
            if result == test_value:
                return jsonify({'status': 'success', 'message': 'Redis OK'})
            else:
                return jsonify({'status': 'error', 'message': 'Redis value mismatch'}), 500
        except redis.RedisError as e:
            return jsonify({'status': 'error', 'message': f'Redis error: {str(e)}'}), 500

    @flask_app.route('/check-login-status', methods=['GET'])
    def check_login_status():
        """
        Verifica o status de autenticação do usuário e retorna is_registered.
        """
        is_registered = current_user.is_authenticated
        user_id = current_user.id if is_registered else None
        
        logger.info(f"Verificação de login: is_registered={is_registered}, user_id={user_id}")
        
        return jsonify({'is_registered': is_registered})
    
    @flask_app.route('/dash_entry', methods=['GET'])
    def dash_entry():
        """
        Entrada para o dashboard Dash, carregando os dados do portfólio.
        """
        user_id = session.get('user_id')
        portfolio = None
        
        try:
            if user_id and current_user.is_authenticated:
                portfolio = portfolio_service.load_portfolio(user_id)
                if portfolio:
                    logger.info(f"Portfólio carregado do banco para user_id {user_id}")
            
            elif 'session_id' in session:
                session_id = session['session_id']
                portfolio_data = redis_client.get(f"portfolio:{session_id}")
                if portfolio_data:
                    portfolio = orjson_loads(portfolio_data)
                    logger.info(f"Portfólio carregado do Redis para session_id: {session_id}, Sessão ID: {session.sid}")
                    # Carrega portfólio do Redis em vez de session['portfolio']
            
            logger.info(f"Acessando dashboard: portfólio presente={bool(portfolio)}")
            
            if not portfolio:
                logger.warning("Nenhum portfólio encontrado, redirecionando para home")
                return redirect(url_for('findash_home'))

            portfolio_dash.layout.children[0].data = portfolio
            return portfolio_dash.index()
            # Removido response.set_cookie(); Flask-Session gerencia cookies
        except RedisError as e:
            # Adicionado tratamento de erro para falhas do Redis
            logger.error(f"Erro ao acessar Redis em /dash_entry: {str(e)}")
            return redirect(url_for('findash_home'))

    @flask_app.route('/signup', methods=['POST'])
    def signup():
        """Cadastra um novo usuário com email e senha."""
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            logger.error("Falha no cadastro: email ou senha não fornecidos")
            return render_template('findash_home.html', 
                                 end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                                 error="Email e senha são obrigatórios")

        if len(password) < 6:
            logger.error("Falha no cadastro: senha curta")
            return render_template('findash_home.html', 
                                 end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                                 error="A senha deve ter pelo menos 6 caracteres")

        try:
            user_id = str(uuid4())
            password_hash = generate_password_hash(password)
            portfolio_service.db.add_user(user_id, email, password_hash)
            # Criar plano cadastrado para o usuário
            portfolio_service.db.add_plan(user_id, plan_type="registered")
            # Autenticar usuário com Flask-Login
            login_user(User(user_id))
            # Atualizar sessão com informações de plano
            session['user_id'] = user_id
            session['is_registered'] = True
            session['plan_type'] = "registered"
            session['tickers_limit'] = 8
            session.permanent = True
            flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
            logger.info(f"Usuário cadastrado: user_id={user_id}, email={email}")
            return render_template('findash_home.html', 
                                 end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                                 success="Cadastro realizado com sucesso! Você pode criar e salvar portfólios.")
        except ValueError as e:
            logger.error(f"Erro no cadastro: {str(e)}")
            return render_template('findash_home.html', 
                                 end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                                 error=str(e))
        
    @flask_app.route('/login', methods=['POST'])
    def login():
        """Autentica um usuário com email e senha."""
        email = request.form.get('email')
        password = request.form.get('password')

        logger.info(f"Tentativa de login: email={email}")

        if not email or not password:
            logger.error("Falha no login: email ou senha não fornecidos")
            return render_template('findash_home.html', 
                                end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                                error="Email e senha são obrigatórios")

        user = portfolio_service.db.get_user_by_email(email)
        if not user or not check_password_hash(user['password_hash'], password):
            logger.error(f"Falha no login: credenciais inválidas para email={email}")
            return render_template('findash_home.html', 
                                end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                                error="Email ou senha inválidos")

        # Autenticar usuário com Flask-Login
        login_user(User(user['id']))
        # Obter plano do usuário
        plan = portfolio_service.db.get_plan_by_user_id(user['id'])
        if not plan:
            logger.error(f"Falha no login: plano não encontrado para user_id={user['id']}")
            return render_template('findash_home.html', 
                                end_date_default=(datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
                                error="Plano não encontrado")

        # Atualizar sessão com informações de plano
        session['user_id'] = user['id']
        session['is_registered'] = True
        session['plan_type'] = plan['plan_type']
        session['tickers_limit'] = plan['tickers_limit']
        session.permanent = True  # ALTERAÇÃO: Sessão de 24 horas para cadastrados
        flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

        # Carregar portfólio salvo, se existir
        try:
            portfolio = portfolio_service.load_portfolio(user['id'])
            if portfolio:
                logger.info(f"Portfólio carregado automaticamente para user_id={user['id']}")
                return redirect(url_for('dash_entry'))
        except ValueError as e:
            logger.error(f"Erro ao carregar portfólio: {str(e)}")

        logger.info(f"Login bem-sucedido: user_id={user['id']}")
        end_date_default = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        return render_template('findash_home.html', 
                            end_date_default=end_date_default,
                            success="Login realizado com sucesso! Você pode criar e salvar portfólios.")

    
    @flask_app.route('/logout', methods=['GET'])
    def logout():
        try:
            if not current_user.is_authenticated:
                session_id = session.get('session_id')
                if session_id:
                    redis_client.delete(f"portfolio:{session_id}")
                    # ALTERAÇÃO: Remove portfólio anônimo do Redis no logout
                session.clear()
            else:
                session.pop('user_id', None)
                session.pop('is_registered', None)
                session.pop('plan_type', None)
                session.pop('tickers_limit', None)
            logout_user()
            logger.info("Logout realizado com sucesso")
            return redirect(url_for('homepage'))
        except RedisError as e:
            # ALTERAÇÃO: Adicionado tratamento de erro para falhas do Redis
            logger.error(f"Erro ao acessar Redis em /logout: {str(e)}")
            return redirect(url_for('homepage'))
    
    @flask_app.route('/blog', methods=['GET'])
    def blog():
        """Placeholder para a página de blog."""
        return render_template('blog.html')

    @flask_app.route('/company', methods=['GET'])
    def company():
        """Placeholder para a página da empresa."""
        return render_template('company.html')
    
    @flask_app.route('/segurai', methods=['GET'])
    def segurai():
        """Renderiza a página do Segurai."""
        return render_template('segurai.html')
    
    
    return flask_app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False)