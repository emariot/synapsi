# Findash/services/database.py
import sqlite3
import os
from datetime import datetime
from werkzeug.security import check_password_hash
from Findash.utils.serialization import orjson_dumps, orjson_loads

class Database:
    
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.abspath(os.path.dirname(__file__))  # Pasta Findash/services
            db_path = os.path.join(base_dir, "..", "data", "portfolios.db")
            db_path = os.path.abspath(db_path)

        self.db_path = db_path

        # Garante que o diretório do banco existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._create_tables()

    def _create_tables(self):
        """Cria tabelas portfolios, plans e cache_index."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Tabela portfolios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    portfolio_data TEXT NOT NULL,
                    name TEXT,  
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, active)
                )
            """)
            # Tabela plans
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    plan_type TEXT NOT NULL,
                    tickers_limit INTEGER DEFAULT 10,
                    ads_enabled BOOLEAN DEFAULT 1,
                    price REAL DEFAULT 0.0,
                    portfolio_limit INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Tabela cache_index
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    tickers_hash TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            # Tabela users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    # ALTERAÇÃO: Método para adicionar usuário
    # Motivo: Salva email e hash da senha no banco
    # Impacto: Usado na rota /signup
    def add_user(self, user_id: str, email: str, password_hash: str):
        """Adiciona um novo usuário ao banco."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                    (user_id, email, password_hash)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise ValueError("Email já cadastrado")
            
    # Adiciona plano para usuário
    # Motivo: Associa plano ao usuário no signup
    # Impacto: Define tickers_limit e portfolio_limit
    def add_plan(self, user_id: str, plan_type: str = "registered"):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            tickers_limit = 8 if plan_type == "registered" else 5
            portfolio_limit = 1 if plan_type == "registered" else 0
            try:
                cursor.execute(
                    """
                    INSERT INTO plans (user_id, plan_type, tickers_limit, ads_enabled, price, portfolio_limit)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, plan_type, tickers_limit, False, 0.0, portfolio_limit)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise ValueError("Plano já existe para o usuário")

    # Busca plano por user_id
    # Motivo: Recupera plan_type e tickers_limit
    # Impacto: Usado em login para atualizar sessão
    def get_plan_by_user_id(self, user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT plan_type, tickers_limit, portfolio_limit
                FROM plans WHERE user_id = ?
                """,
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "plan_type": row[0],
                    "tickers_limit": row[1],
                    "portfolio_limit": row[2]
                }
            return None

    # ALTERAÇÃO: Método para verificar credenciais
    # Motivo: Valida email e senha no login
    # Impacto: Usado na rota /login
    def get_user_by_email(self, email: str):
        """Busca usuário por email e retorna id e password_hash."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, password_hash FROM users WHERE email = ?",
                (email,)
            )
            row = cursor.fetchone()
            if row:
                return {'id': row[0], 'password_hash': row[1]}
            return None
    
    def get_user_by_id(self, user_id: str):
        """Busca usuário por ID e retorna id e password_hash."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, password_hash FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {'id': row[0], 'password_hash': row[1]}
            return None

    def has_active_portfolio(self, user_id: str) -> bool:
        """Verifica se o usuário possui um portfólio ativo."""
        # Novo método para verificar portfólio ativo
        # Motivo: Move a lógica SQL de portfolio_services.py para manter separação de responsabilidades
        # Impacto: Simplifica save_portfolio e centraliza acesso ao banco
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM portfolios WHERE user_id = ? AND active = 1",
                (user_id,)
            )
            return cursor.fetchone() is not None

    def add_portfolio(self, user_id, portfolio_data, name=None):

        """Adiciona portfólio com dados essenciais, verificando limite de 1 ativo."""
        print(f"Chamando add_portfolio para user_id={user_id}, name={name}")  # Log temporário
        if not portfolio_data:
            print(f"Erro: portfolio_data é None para user_id={user_id}")
            raise ValueError("Dados do portfólio não podem ser None")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Verifica portfólios ativos
            cursor.execute(
                "SELECT COUNT(*) FROM portfolios WHERE user_id = ? AND active = 1",
                (user_id,)
            )

            count = cursor.fetchone()[0]
            print(f"Portfólios ativos encontrados: {count}")
            if count >= 1:
                raise ValueError("Usuário já possui um portfólio ativo")

            # Validar chaves necessárias
            required_keys = ['tickers', 'quantities', 'start_date', 'end_date']
            missing_keys = [key for key in required_keys if key not in portfolio_data]
            if missing_keys:
                print(f"Erro: portfolio_data incompleto para user_id={user_id}, faltam chaves: {missing_keys}")
                raise ValueError(f"Dados do portfólio incompletos: faltam {missing_keys}")
        
            essential_data = {
                'tickers': portfolio_data['tickers'],
                'quantities': portfolio_data['quantities'],
                'start_date': portfolio_data['start_date'],
                'end_date': portfolio_data['end_date'],
                'name': name or 'Portfólio 1'
            }
            portfolio_data_json = orjson_dumps(essential_data).decode('utf-8')
            print(f"Salvando portfolio_data: {portfolio_data_json}")  # Log temporário
            # Insere novo portfólio
            cursor.execute(
                "INSERT INTO portfolios (user_id, portfolio_data, name, active) VALUES (?, ?, ?, 1)",
                (user_id, portfolio_data_json, name)
            )
            conn.commit()
            print(f"Portfólio inserido com sucesso para user_id={user_id}")  # Log temporário

    def update_portfolio(self, user_id, portfolio_data, name=None):
        """Atualiza portfólio ativo com dados essenciais."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Verifica se existe portfólio ativo
            cursor.execute(
                "SELECT id FROM portfolios WHERE user_id = ? AND active = 1",
                (user_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Nenhum portfólio ativo encontrado para o usuário")
            # Serializa apenas os dados essenciais
            essential_data = {
                'tickers': portfolio_data['tickers'],
                'quantities': portfolio_data['quantities'],
                'start_date': portfolio_data['start_date'],
                'end_date': portfolio_data['end_date'],
                'name': name
            }
            portfolio_data_json = orjson_dumps(essential_data).decode('utf-8')
            # Atualiza portfólio
            cursor.execute(
                "UPDATE portfolios SET portfolio_data = ?, name = ?, created_at = CURRENT_TIMESTAMP WHERE id = ?",
                (portfolio_data_json, name, row[0])
            )
            conn.commit()

    def get_active_portfolios(self, user_id):
        """Retorna portfólios ativos do usuário com dados essenciais."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT portfolio_data, name FROM portfolios WHERE user_id = ? AND active = 1",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [{'portfolio_data': orjson_loads(row[0]), 'name': row[1]} for row in rows]
        
    def add_cache_index(self, user_id, tickers_hash, start_date, end_date, file_path, expires_at):
        """Adiciona entrada ao cache_index."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO cache_index (user_id, tickers_hash, start_date, end_date, file_path, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, tickers_hash, start_date, end_date, file_path, expires_at)
            )
            conn.commit()

    def get_cache_index(self, user_id, tickers_hash, start_date, end_date):
        """Busca entrada no cache_index."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT file_path, expires_at FROM cache_index
                WHERE user_id = ? AND tickers_hash = ? AND start_date = ? AND end_date = ?
                """,
                (user_id, tickers_hash, start_date, end_date)
            )
            row = cursor.fetchone()
            if row and datetime.fromisoformat(row[1]) > datetime.now():
                return row[0]
            return None