import numpy as np


def validate_upload_basic(uploaded_file, allowed_exts, max_mb, label):
    if uploaded_file is None:
        return False, f"Nenhum arquivo enviado para {label}."

    import os

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in allowed_exts:
        return False, f"Formato inválido para {label}. Use: {', '.join(sorted(allowed_exts))}."

    size_bytes = getattr(uploaded_file, "size", None)
    if size_bytes is not None and size_bytes > max_mb * 1024 * 1024:
        return False, f"Arquivo muito grande para {label}. Limite: {max_mb} MB."

    return True, ""


def normalize_numeric_value(val, fallback=0.0, min_value=None, max_value=None):
    try:
        num = float(val)
    except (TypeError, ValueError):
        num = float(fallback)
    if not np.isfinite(num):
        num = float(fallback)
    if min_value is not None:
        num = max(min_value, num)
    if max_value is not None:
        num = min(max_value, num)
    return num


def preparar_df_app(df_source, prazo_selecionado):
    df_app_local = df_source.copy()
    if df_app_local.empty:
        return df_app_local

    if prazo_selecionado not in {"Preço_7", "Preço_14", "Preço_21", "Preço_28"}:
        prazo_selecionado = "Preço_7"

    df_app_local["Preço Atual"] = df_app_local[prazo_selecionado].fillna(df_app_local["Preço_7"])
    df_app_local["Preço Anterior"] = df_app_local["Preço Atual"] * df_app_local["Fator_Anterior"]
    df_app_local["Preço Anterior"] = np.where(df_app_local["Preço Anterior"] == 0, 1, df_app_local["Preço Anterior"])
    df_app_local["Desconto %"] = (
        (df_app_local["Preço Anterior"] - df_app_local["Preço Atual"]) / df_app_local["Preço Anterior"] * 100
    ).round(1)

    def gerar_status(row):
        perc = row["Desconto %"]
        if row["Preço Atual"] < row["Preço Anterior"]:
            return f"🟢 Baixou! (-{abs(perc)}%)"
        if row["Preço Atual"] > row["Preço Anterior"]:
            return f"🔴 Aumentou! (+{abs(perc)}%)"
        return "⚫ Igual"

    df_app_local["Status"] = df_app_local.apply(gerar_status, axis=1)
    return df_app_local
