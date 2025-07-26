import pandas as pd

def gerar_column_defs_ag_grid(df: pd.DataFrame) -> list[dict]:
    column_defs = []

    for col in df.columns:
        if col == "KPI":
            column_defs.append({
                "field": col,
                "headerName": col,
                "pinned": "left",
                "cellStyle": {
                    "fontWeight": "bold",
                    "backgroundColor": "#f0f0f0"
                }
            })
        else:
            column_defs.append({
                "field": col,
                "headerName": col,
                "type": "numericColumn",
                "cellStyle": {
                    "styleConditions": [
                        # SHARPE e SORTINO - quanto maior melhor
                        {
                            "condition": "['sharpe','sortino'].includes(params.data['KPI']?.toLowerCase()) && params.value > 1",
                            "style": {"backgroundColor": "green", "color": "white"}
                        },
                        {
                            "condition": "['sharpe','sortino'].includes(params.data['KPI']?.toLowerCase()) && params.value < 0.5",
                            "style": {"backgroundColor": "red", "color": "white"}
                        },
                        {
                            "condition": "['sharpe','sortino'].includes(params.data['KPI']?.toLowerCase())",
                            "style": {"backgroundColor": "orange", "color": "black"}
                        },

                        # VOLATILIDADE e MAX DRAWDOWN - quanto menor melhor
                        {
                            "condition": "['volatilidade','max_drawdown'].includes(params.data['KPI']?.toLowerCase()) && params.value < 0.15",
                            "style": {"backgroundColor": "green", "color": "white"}
                        },
                        {
                            "condition": "['volatilidade','max_drawdown'].includes(params.data['KPI']?.toLowerCase()) && params.value > 0.3",
                            "style": {"backgroundColor": "red", "color": "white"}
                        },
                        {
                            "condition": "['volatilidade','max_drawdown'].includes(params.data['KPI']?.toLowerCase())",
                            "style": {"backgroundColor": "orange", "color": "black"}
                        },

                        # RETORNO MÉDIO ANUAL e ALPHA - quanto maior melhor
                        {
                            "condition": "['retorno_medio_anual','alpha'].includes(params.data['KPI']?.toLowerCase()) && params.value > 0.05",
                            "style": {"backgroundColor": "green", "color": "white"}
                        },
                        {
                            "condition": "['retorno_medio_anual','alpha'].includes(params.data['KPI']?.toLowerCase()) && params.value < 0",
                            "style": {"backgroundColor": "red", "color": "white"}
                        },
                        {
                            "condition": "['retorno_medio_anual','alpha'].includes(params.data['KPI']?.toLowerCase())",
                            "style": {"backgroundColor": "orange", "color": "black"}
                        },

                        # BETA - ideal próximo de 1
                        {
                            "condition": "params.data['KPI']?.toLowerCase() === 'beta' && params.value >= 0.8 && params.value <= 1.2",
                            "style": {"backgroundColor": "green", "color": "white"}
                        },
                        {
                            "condition": "params.data['KPI']?.toLowerCase() === 'beta' && (params.value < 0.6 || params.value > 1.4)",
                            "style": {"backgroundColor": "red", "color": "white"}
                        },
                        {
                            "condition": "params.data['KPI']?.toLowerCase() === 'beta'",
                            "style": {"backgroundColor": "orange", "color": "black"}
                        }
                    ]
                }
            })

    return column_defs
