import joblib
import pandas as pd

# Carrega as features usadas nos modelos
MODELO_FEATURES = joblib.load('Segurai/models/modelo_features.joblib')

def preparar_dados_entrada(dados):

    """
    Monta o DataFrame de entrada para os modelos, garantindo que todas as colunas 
    estejam presentes e na ordem correta.
    
    Parâmetros:
        dados (dict): dados brutos do formulário com chaves como 'idade', 'renda', etc.
        
    Retorna:
        DataFrame com as features no formato do treino.
    """

    X = pd.DataFrame([{
        'idade': dados['idade'],
        'renda': dados['renda'],
        'sinistro': dados['sinistro'],
        f'uf_{dados["uf"]}': 1,
        f'tipo_seguro_{dados["tipo_seguro"]}': 1,
        f'estado_civil_{dados["estado_civil"]}': 1
    }])


    # Zera as colunas ausentes para garantir o mesmo formato das features do treino
    for col in MODELO_FEATURES:
        if col not in X.columns:
            X[col] = 0
    
    # Reordena as colunas para a mesma ordem do treino
    X = X[MODELO_FEATURES]

    return X