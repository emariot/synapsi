import joblib

# Carrega as features usadas nos modelos
MODELO_FEATURES = joblib.load('Segurai/models/modelo_features.joblib')

# Carrega o LabelEncoder usado no treino
le = joblib.load('Segurai/models/label_encoder.joblib')

def preparar_dados_entrada(dados):
    import pandas as pd

    # Cria o dataframe com as variáveis básicas
    X = pd.DataFrame([{
        'idade': dados['idade'],
        'renda': dados['renda'],
        'sinistro': dados['sinistro'],
        f'uf_{dados["uf"]}': 1,
        f'tipo_seguro_{dados["tipo_seguro"]}': 1,
        f'estado_civil_{dados["estado_civil"]}': 1
    }])

    # Garante que todas as colunas do treino estejam presentes
    for col in MODELO_FEATURES:
        if col not in X.columns:
            X[col] = 0
    return X[MODELO_FEATURES]