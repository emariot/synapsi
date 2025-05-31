# SegurAI/models/calculo_score.py

def calcular_score(idade: int, uf: str, tipo_seguro: str) -> dict:
    score = 100

    # Penalizações por tipo de seguro
    if tipo_seguro == "auto":
        score -= 20
    elif tipo_seguro == "vida":
        score -= 10
    elif tipo_seguro == "residencial":
        score -= 5

    # Penalização por UF
    if uf in ["RJ", "SP"]:
        score -= 15
    else:
        score -= 5

    # Penalização por idade
    if idade < 25:
        score -= 25
    elif idade > 60:
        score -= 10

    classificacao = (
        "Alto" if score < 60 else
        "Médio" if score < 85 else
        "Baixo"
    )

    return {
        "score": round(score, 2),
        "classificacao": classificacao
    }
