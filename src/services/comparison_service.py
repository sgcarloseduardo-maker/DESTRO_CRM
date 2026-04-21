import pandas as pd


def build_weekly_comparison(df_atual: pd.DataFrame, df_anterior: pd.DataFrame) -> pd.DataFrame:
    if df_atual.empty and df_anterior.empty:
        return pd.DataFrame(columns=["codigo_destro", "preco_7_atual", "preco_7_anterior", "variacao_pct"])

    if "codigo_destro" not in df_atual.columns:
        df_atual = pd.DataFrame(columns=["codigo_destro", "preco_7"])
    if "preco_7" not in df_atual.columns:
        df_atual = df_atual.copy()
        df_atual["preco_7"] = 0.0

    if "codigo_destro" not in df_anterior.columns:
        df_anterior = pd.DataFrame(columns=["codigo_destro", "preco_7"])
    if "preco_7" not in df_anterior.columns:
        df_anterior = df_anterior.copy()
        df_anterior["preco_7"] = 0.0

    atual = df_atual[["codigo_destro", "preco_7"]].rename(columns={"preco_7": "preco_7_atual"})
    ant = df_anterior[["codigo_destro", "preco_7"]].rename(columns={"preco_7": "preco_7_anterior"})
    merged = atual.merge(ant, on="codigo_destro", how="outer")
    merged["preco_7_atual"] = pd.to_numeric(merged["preco_7_atual"], errors="coerce").fillna(0.0)
    merged["preco_7_anterior"] = pd.to_numeric(merged["preco_7_anterior"], errors="coerce").fillna(0.0)

    denom = merged["preco_7_anterior"].replace(0, 1)
    merged["variacao_pct"] = ((merged["preco_7_atual"] - merged["preco_7_anterior"]) / denom * 100).round(2)

    def tendencia(row: pd.Series) -> str:
        atual = float(row["preco_7_atual"])
        anterior = float(row["preco_7_anterior"])
        if anterior == 0 and atual > 0:
            return "NOVO"
        if anterior == 0 and atual == 0:
            return "SEM_BASE"
        if atual > anterior:
            return "SUBIU"
        if atual < anterior:
            return "CAIU"
        return "ESTAVEL"

    merged["tendencia_preco"] = merged.apply(tendencia, axis=1)
    return merged
