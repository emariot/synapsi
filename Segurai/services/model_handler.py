import joblib

CAMINHOS_MODELOS = {
    'Regressão Logística': 'SegurAI/models/regressao_logistica.joblib',
    'Random Forest': 'SegurAI/models/random_forest.joblib',
    'XGBoost': 'SegurAI/models/xgboost.joblib',
    'LightGBM': 'SegurAI/models/lightgbm.joblib'
}

def carregar_modelos():
    '''Carrega todos os modelos salvos como objetos do Python'''
    return {nome: joblib.load(caminho) for nome, caminho in CAMINHOS_MODELOS.items()}

def prever_todos_modelos(X_input, modelos, label_encoder):
    '''Executa a previsão em todos os modelos carregados.'''
    resultados = []

    for nome, modelo in modelos.items():
        classe_predita = modelo.predict(X_input)[0]
        score_proba = modelo.predict_proba(X_input)[0].max()

        resultados.append({
            'modelo': nome,
            'classe': label_encoder.inverse_transform([classe_predita])[0],
            'score': round(score_proba, 2)
        })
    return resultados