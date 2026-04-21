import re
from typing import Dict, Tuple

import pandas as pd

from src.config.schema_contract import CONTRACTS


def _normalize_colname(name: str) -> str:
    n = str(name).strip().lower()
    n = re.sub(r"\s+", " ", n)
    n = n.replace("/", " ")
    return n


def _canonicalize_columns(df: pd.DataFrame, domain: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
    mapping = CONTRACTS[domain].canonical_map
    resolved: Dict[str, str] = {}
    renamed = {}
    for c in df.columns:
        key = _normalize_colname(c)
        canonical = mapping.get(key)
        if canonical:
            renamed[c] = canonical
            resolved[canonical] = c
    out = df.rename(columns=renamed)
    return out, resolved


def _clean_code(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.replace(r"\D", "", regex=True).str.strip()


def normalize_semanal(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], list]:
    out, resolved = _canonicalize_columns(df, "semanal")
    warnings = []

    norm_original = {_normalize_colname(c): c for c in df.columns}

    def pick_contains(*tokens: str):
        for norm, original in norm_original.items():
            if all(t in norm for t in tokens):
                return original
        return None

    if "codigo_destro" not in out.columns:
        col = pick_contains("codigo")
        if col:
            out["codigo_destro"] = df[col]
            resolved["codigo_destro"] = col

    if "descricao_produto" not in out.columns:
        col = pick_contains("descricao")
        if col:
            out["descricao_produto"] = df[col]
            resolved["descricao_produto"] = col

    if "preco_7" not in out.columns:
        col = pick_contains("vista")
        if col:
            out["preco_7"] = df[col]
            resolved["preco_7"] = col

    if "preco_14" not in out.columns:
        col = pick_contains("14", "dias")
        if col:
            out["preco_14"] = df[col]
            resolved["preco_14"] = col

    if "preco_21" not in out.columns:
        col = pick_contains("21", "dias")
        if col:
            out["preco_21"] = df[col]
            resolved["preco_21"] = col

    if "preco_28" not in out.columns:
        col = pick_contains("28", "dias")
        if col:
            out["preco_28"] = df[col]
            resolved["preco_28"] = col

    if "ean" not in out.columns:
        col = pick_contains("barras")
        if col:
            out["ean"] = df[col]
            resolved["ean"] = col

    if "codigo_destro" not in out.columns and out.shape[1] > 0:
        out["codigo_destro"] = _clean_code(out.iloc[:, 0])
        warnings.append("codigo_destro inferido da primeira coluna.")
    if "descricao_produto" not in out.columns and out.shape[1] > 1:
        out["descricao_produto"] = out.iloc[:, 1].fillna("").astype(str)
        warnings.append("descricao_produto inferida da segunda coluna.")

    for col in ["preco_7", "preco_14", "preco_21", "preco_28", "estoque_atual"]:
        if col not in out.columns:
            out[col] = 0
            warnings.append(f"{col} ausente; preenchido com 0.")

    out["codigo_destro"] = _clean_code(out["codigo_destro"])
    out["descricao_produto"] = out["descricao_produto"].fillna("").astype(str).str.strip()
    for col in ["preco_7", "preco_14", "preco_21", "preco_28", "estoque_atual"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    for opt in ["ean", "industria", "marca", "categoria", "st_flag"]:
        if opt not in out.columns:
            out[opt] = ""

    out = out[out["codigo_destro"] != ""]
    out = out.drop_duplicates(subset=["codigo_destro"], keep="last")

    keep = CONTRACTS["semanal"].required_columns + CONTRACTS["semanal"].optional_columns
    return out[keep].copy(), resolved, warnings


def normalize_abc(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], list]:
    out, resolved = _canonicalize_columns(df, "abc")
    warnings = []

    if "codigo_destro" not in out.columns and out.shape[1] > 0:
        out["codigo_destro"] = _clean_code(out.iloc[:, 0])
        warnings.append("codigo_destro inferido da primeira coluna.")
    if "curva_abc" not in out.columns:
        if out.shape[1] > 1:
            out["curva_abc"] = out.iloc[:, 1]
            warnings.append("curva_abc inferida da segunda coluna.")
        else:
            out["curva_abc"] = "C"
            warnings.append("curva_abc ausente; preenchida com C.")

    out["codigo_destro"] = _clean_code(out["codigo_destro"])
    out["curva_abc"] = out["curva_abc"].fillna("C").astype(str).str.strip().str.upper().str[:1]
    if "descricao_produto" not in out.columns:
        out["descricao_produto"] = ""
    out["descricao_produto"] = out["descricao_produto"].fillna("").astype(str)

    out = out[out["codigo_destro"] != ""]
    out = out.drop_duplicates(subset=["codigo_destro"], keep="last")
    keep = CONTRACTS["abc"].required_columns + CONTRACTS["abc"].optional_columns
    return out[keep].copy(), resolved, warnings


def normalize_campanhas(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], list]:
    out, resolved = _canonicalize_columns(df, "campanhas")
    warnings = []

    if "codigo_destro" not in out.columns and out.shape[1] > 0:
        out["codigo_destro"] = _clean_code(out.iloc[:, 0])
        warnings.append("codigo_destro inferido da primeira coluna.")
    if "flag_campanha" not in out.columns:
        out["flag_campanha"] = True
        warnings.append("flag_campanha ausente; preenchida com True.")
    if "descricao_produto" not in out.columns:
        out["descricao_produto"] = ""
    if "nome_campanha" not in out.columns:
        out["nome_campanha"] = "campanha_geral"

    out["codigo_destro"] = _clean_code(out["codigo_destro"])
    out["descricao_produto"] = out["descricao_produto"].fillna("").astype(str)
    out["nome_campanha"] = out["nome_campanha"].fillna("campanha_geral").astype(str)
    out["flag_campanha"] = out["flag_campanha"].astype(str).str.lower().isin(["1", "true", "sim", "y", "yes"])

    out = out[out["codigo_destro"] != ""]
    out = out.drop_duplicates(subset=["codigo_destro", "nome_campanha"], keep="last")
    keep = CONTRACTS["campanhas"].required_columns + CONTRACTS["campanhas"].optional_columns
    return out[keep].copy(), resolved, warnings
