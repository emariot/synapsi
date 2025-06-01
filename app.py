from flask import Flask, session, redirect, url_for, render_template, request, jsonify, make_response, Response, flash
from flask_session import Session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from redis.exceptions import RedisError, ConnectionError
import redis
import os
import re
import logging
import shutil
from uuid import uuid4
from datetime import timedelta, datetime
from Findash.app_dash import init_dash
from Findash.services.portfolio_services import PortfolioService
from utils.serialization import orjson_dumps, orjson_loads
from werkzeug.security import generate_password_hash, check_password_hash
from Segurai.app_dash import init_segurai_dash
import random

from Segurai.models.calculo_score import calcular_score

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

def create_app():
    app = Flask(__name__)
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

    try:
        app.config['SESSION_REDIS'].ping()
        data_redis.ping()
        logger.info("Redis de sessão e dados conectados.")
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

    def load_portfolio_by_context():
        """Tenta carregar o portfólio do Redis ou banco (autenticado)."""
        user_id = session.get('user_id')
        if user_id and current_user.is_authenticated:
            logger.debug(f"Carregando portfólio do BANCO para user_id={user_id}")
            return portfolio_service.load_portfolio(user_id)

        if user_id:
            logger.debug(f"Carregando portfólio do REDIS para user_id={user_id}")
            data = data_redis.get(f"portfolio:{user_id}")
            return orjson_loads(data) if data else None
        
        logger.warning("load_portfolio_by_context chamado sem user_id definido.")
        return None

    @app.route('/')
    def homepage():
        return render_template('homepage.html')  # Crie esse template básico

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
        """Retorna a lista de tickers disponíveis."""
        return Response(
            orjson_dumps(TICKERS),
            mimetype='application/json'
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
                portfolio = load_portfolio_by_context()
                if not portfolio:
                     flash("Nenhum portfólio encontrado. Crie um novo.", "warning")
                     return redirect(url_for('findash_home'))
            
            '''
            Substituir para apenas anexar os metadados (depois de realizado todos os testes)
            # Anexa metadados de controle (plano) ao portfólio
            portfolio.update({
                'is_registered': session.get('is_registered', False),
                'plan_type': session.get('plan_type', 'free'),
                'tickers_limit': session.get('tickers_limit', 5)
            })
            '''
            # Preparar o portfólio para enviar ao Dash
            portfolio = {
                'tickers': portfolio.get('tickers', []),
                'quantities': portfolio.get('quantities', []),
                'start_date': portfolio.get('start_date', ''),
                'end_date': portfolio.get('end_date', ''),
                'portfolio': portfolio.get('portfolio', {}), 
                'portfolio_values': portfolio.get('portfolio_values', {}),
                'portfolio_return': portfolio.get('portfolio_return', {}),
                'individual_returns': portfolio.get('individual_returns', {}),
                'ibov_return': portfolio.get('ibov_return', {}),
                'table_data': portfolio.get('table_data', []),
                'dividends': portfolio.get('dividends', {}),
                'setor_pesos': portfolio.get('setor_pesos', {}),
                'setor_pesos_financeiros': portfolio.get('setor_pesos_financeiros', {}),
                'individual_daily_returns': portfolio.get('individual_daily_returns', {}),
                'portfolio_daily_return': portfolio.get('portfolio_daily_return', {}),
                'portfolio_name': portfolio.get('portfolio_name', 'Portfólio 1'),
                'is_registered': session.get('is_registered', False),
                'plan_type': session.get('plan_type', 'free'),
                'tickers_limit': session.get('tickers_limit', 5)
            }
            # Serializar com orjson e salvar na sessão
            session['initial_portfolio'] = orjson_dumps(portfolio).decode('utf-8')
            session.modified = True
            logger.info(f"Portfólio salvo na sessão para Dash | user_id={user_id} | tickers={portfolio['tickers']}")

            return dash_app.index()
        
        except Exception as e:
            logger.error(f"Erro ao carregar /dash_entry | user_id={user_id}: {str(e)}")
            flash("Erro ao carregar o portfólio. Tente novamente.", "danger")
            return redirect(url_for('findash_home'))

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
            portfolio = portfolio_service.load_portfolio(user_id)
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
        uf = request.form.get('uf')
        tipo = request.form.get('tipo_seguro')

        # Simulação de cálculo do modelo (placeholder)
        resultado = calcular_score(idade, uf, tipo) 

        segurai_data = {
            'idade': idade,
            'uf': uf,
            'tipo_seguro': tipo,
            'score': resultado["score"],
            'classificacao': resultado["classificacao"]
        }
        # Salvar como JSON na sessão
        session['segurai_data'] = orjson_dumps(segurai_data).decode('utf-8')

        return redirect(url_for('dash_entry_segurai'))

    @app.route('/dash_entry_segurai', methods=['GET'])
    def dash_entry_segurai():
        if 'segurai_data' not in session:
            return redirect(url_for('segurai_home'))
       
        return segurai_dash.index()
    
    @app.route('/ver-session')
    def ver_session():
        print(session.keys())  # Mostra no console do servidor
        return str(list(session.keys()))  # Retorna as chaves como resposta HTTP

    
    return app

if __name__ == "__main__":

    flask_app = create_app()
    flask_app.run(debug=True, use_reloader=False)