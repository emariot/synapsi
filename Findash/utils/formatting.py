def format_kpi(kpi_name: str, value: float | None) -> str:
    """
    Formata o valor de um KPI com base em seu nome.

    Args:
        kpi_name (str): Nome do KPI (ex.: "sharpe", "volatilidade").
        value (float | None): Valor bruto do KPI ou None.

    Returns:
        str: Valor formatado como string (ex.: "2.34", "5.67%", "N/A").
    """
    if value is None:
        return "N/A"

    # KPIs que usam formato percentual
    percentage_kpis = ["volatilidade", "drawdown", "alpha", "beta"]
    if kpi_name.lower() in percentage_kpis:
        return f"{value:.2f}%"
    
    # Outros KPIs (ex.: Sharpe, Sortino, Retorno) usam formato decimal
    return f"{value:.2f}"