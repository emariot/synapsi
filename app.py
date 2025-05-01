# app.py
from flask import Flask, render_template, request, redirect, session, url_for, Response, jsonify
from datetime import datetime, timedelta
from Findash.app_dash import init_dash as init_portfolio_dash
from flask_session import Session
from Findash.services.portfolio_services import PortfolioService
from Findash.utils.serialization import orjson_dumps, orjson_loads
import orjson
import redis
import os
from uuid import uuid4

def create_app():
    # Inicializar Flask
    flask_app = Flask(__name__)
    flask_app.secret_key = "123456"
    flask_app.config['SESSION_TYPE'] = 'filesystem'
    Session(flask_app)

    # Inicializa o cliente Redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    # Inicializar o serviço
    portfolio_service = PortfolioService()
    portfolio_service.redis_client = redis_client

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
        end_date_default = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        return render_template('findash_home.html', end_date_default=end_date_default)

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
        session['user_authenticated'] = True

        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        tickers = request.form.getlist('tickers[]')
        quantities = request.form.getlist('quantities[]')

        try:
            quantities = [int(q) for q in quantities]
            # Criar o portfólio usando o serviço
            portfolio = portfolio_service.create_portfolio(
                tickers=tickers,
                quantities=quantities,
                start_date=start_date,
                end_date=end_date
            )
            # Armazenar na sessão
            session['portfolio'] = portfolio
            return redirect(url_for('dash_entry'))
        except ValueError as e:
            end_date_default = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            return render_template('findash_home.html', 
                                end_date_default=end_date_default,
                                error=str(e))
        

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

    @flask_app.route('/dash_entry', methods=['GET'])
    def dash_entry():
        """
        Entrada para o dashboard Dash, carregando os dados do portfólio da sessão.
        """
        if 'portfolio' not in session:
            return redirect(url_for('home'))
        
        portfolio = session['portfolio']
        portfolio_dash.layout.children[0].data = portfolio  # Pré-carrega o dcc.Store
        portfolio_dash.layout.children[2].children[0].children[1].value = portfolio['start_date']
        portfolio_dash.layout.children[2].children[0].children[2].value = portfolio['end_date']
        
        return portfolio_dash.index()

    @flask_app.route('/signup', methods=['POST'])
    def signup():
        """Placeholder para signup (não implementado)."""
        return redirect('/')

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
    app.run(debug=True)