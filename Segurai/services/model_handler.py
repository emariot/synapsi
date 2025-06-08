import joblib

CAMINHOS_MODELOS = {
    'Regressão Logística': 'SegurAI/models/regressao_logistica.joblib',
    'Random Forest': 'SegurAI/models/random_forest.joblib',
    'XGBoost': 'SegurAI/models/xgboost.joblib',
    'LightGBM': 'SegurAI/models/lightgbm.joblib'
}

def carregar_modelos():
    '''Carrega todos os modelos salvos como objetos do Python'''
    modelos =  {nome: joblib.load(caminho) for nome, caminho in CAMINHOS_MODELOS.items()}
    # Carregar o scaler da Regressão Logística separadamente
    scaler_rl = joblib.load('Segurai/models/scaler_rl.joblib')

    return modelos, scaler_rl

classes_risco = {0: 'baixo', 1: 'médio', 2: 'alto'}
def prever_todos_modelos(X_input, modelos, scaler_rl):
    """
    Executa a previsão em todos os modelos carregados.

    Parâmetros:
        X_input (DataFrame): entrada com as features no formato do treino.
        modelos (dict): dicionário com os modelos carregados.

    Retorna:
        list: lista de dicionários com modelo, classe prevista e score.
    """

    resultados = []

    for nome, modelo in modelos.items():
        if nome == 'Regressão Logística':
            X_proc = scaler_rl.transform(X_input)
        else:
            X_proc = X_input

        classe_predita = modelo.predict(X_proc)[0]
        score_proba = modelo.predict_proba(X_proc)[0].max()

        classe_nome = classes_risco.get(classe_predita, 'desconhecido')


        resultados.append({
            'modelo': nome,
            'classe': classe_nome,
            'score': round(score_proba, 2)
        })

    return resultados