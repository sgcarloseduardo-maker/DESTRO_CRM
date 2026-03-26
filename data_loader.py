import hashlib
import logging
import os
import re
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

EXPECTED_SHEETS = [
    "Curva ABC_Semanal",
    "Industrias",
    "Marcas",
    "BateuLevou",
    "Banco_Dados_Semanal",
    "TO PODENDO",
    "COLGATE",
]

EXPECTED_OUTPUT_COLUMNS = [
    "Código",
    "Descrição",
    "Preço_7",
    "Preço_14",
    "Preço_21",
    "Preço_28",
    "ST_Flag",
    "Categoria",
    "Indústria",
    "Marca",
    "Camp_Bateu",
    "Camp_ToPodendo",
    "Camp_Colgate",
    "Curva_ABC",
    "Meta_Mensal",
    "Fator_Anterior",
]


def _limpar_industria(val):
    val_str = str(val)
    match = re.search(r'\"(.*?)\"', val_str)
    if match:
        return match.group(1).strip()
    return val_str.replace("(", "").replace(")", "").replace("'", "").replace('"', "").split(",")[0].strip()


def _manter_categoria_completa(txt):
    s = "" if txt is None else str(txt).strip()
    s = re.sub(r"\s+", " ", s).strip()
    if s.lower() == "nan" or s == "":
        return ""
    return s


def _deterministic_index_from_key(key: str, size: int) -> int:
    if size <= 0:
        return 0
    digest = hashlib.sha256(str(key).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % size


def _deterministic_fator_anterior(key: str) -> float:
    digest = hashlib.sha256(str(key).encode("utf-8")).hexdigest()
    bucket = int(digest[8:10], 16) % 100
    if bucket < 50:
        return 1.0
    if bucket < 70:
        return 1.05
    if bucket < 80:
        return 1.15
    return 0.95


def _collect_sheet_warnings(excel_file: pd.ExcelFile) -> List[str]:
    warnings = []
    missing = [s for s in EXPECTED_SHEETS if s not in excel_file.sheet_names]
    if missing:
        warnings.append(f"Abas ausentes na planilha: {', '.join(missing)}.")
    return warnings


def load_crm_data(planilha_path: str) -> Tuple[pd.DataFrame, List[str], List[str], str]:
    """Retorna (df, curva_abc_codigos, warnings, fatal_error)."""
    if not os.path.exists(planilha_path):
        return pd.DataFrame(), [], [], "PLANILHA_NAO_ENCONTRADA"

    warnings: List[str] = []
    try:
        excel_file = pd.ExcelFile(planilha_path, engine="openpyxl")
        warnings.extend(_collect_sheet_warnings(excel_file))
    except Exception as exc:
        logger.exception("Falha ao abrir planilha: %s", exc)
        return pd.DataFrame(), [], [], "PLANILHA_CORROMPIDA_OU_INVALIDA"

    try:
        df_abc = pd.read_excel(
            planilha_path, sheet_name="Curva ABC_Semanal", header=None, engine="openpyxl"
        )
        if 1 not in df_abc.columns:
            warnings.append("Aba 'Curva ABC_Semanal' sem coluna índice 1 esperada.")
            curva_abc_codigos = []
        else:
            col_b = df_abc[1].astype(str)
            mask_tante = col_b.str.contains("TANTE: 999", na=False)
            idx_tante = df_abc.index[mask_tante]
            curva_abc_codigos = []

            if len(idx_tante) > 0:
                linha_inicio = idx_tante[0] + 2
                for i in range(linha_inicio, len(df_abc)):
                    val = str(df_abc.iloc[i, 1]).strip()
                    if (val == "" or val.lower() == "nan") and str(df_abc.iloc[i, 0]).strip().lower() in ["", "nan"]:
                        break
                    cod_val = str(df_abc.iloc[i, 0])
                    cod_limpo = re.sub(r"\D", "", cod_val.split("-")[0])
                    if cod_limpo:
                        curva_abc_codigos.append(cod_limpo)
            else:
                warnings.append("Marcador 'TANTE: 999' não encontrado em 'Curva ABC_Semanal'.")
    except Exception as exc:
        logger.exception("Erro ao ler aba Curva ABC: %s", exc)
        curva_abc_codigos = []

    try:
        df_ind = pd.read_excel(
            planilha_path, sheet_name="Industrias", skiprows=1, header=None, engine="openpyxl"
        )
        lista_industrias = sorted([i for i in df_ind[0].apply(_limpar_industria).dropna().unique() if i != ""])
    except Exception:
        lista_industrias = ["Unilever", "Nestlé"]
        warnings.append("Usando fallback de indústrias por falha na aba 'Industrias'.")

    try:
        df_marcas = pd.read_excel(
            planilha_path, sheet_name="Marcas", skiprows=1, header=None, engine="openpyxl"
        )
        lista_marcas_reais = sorted(
            [m.strip() for m in df_marcas[0].dropna().astype(str) if m.strip().lower() != "nan" and m.strip() != ""]
        )
    except Exception:
        lista_marcas_reais = ["Omo", "Ninho"]
        warnings.append("Usando fallback de marcas por falha na aba 'Marcas'.")

    marcas_sorted = sorted(lista_marcas_reais, key=len, reverse=True)

    def achar_marca(desc):
        desc_up = str(desc).upper()
        for m in marcas_sorted:
            if re.search(r"\b" + re.escape(m.upper()) + r"\b", desc_up):
                return m
        return "Outra Marca"

    try:
        df_bateu = pd.read_excel(planilha_path, sheet_name="BateuLevou", engine="openpyxl")
        df_bateu["Desc_Norm"] = df_bateu["DESCRICAO"].astype(str).apply(lambda x: re.sub(r"\s+", " ", x.strip().upper()))
        dict_bateu_ind = df_bateu.set_index("Desc_Norm")["INDUSTRIA"].to_dict() if "INDUSTRIA" in df_bateu.columns else {}
        dict_bateu_mar = df_bateu.set_index("Desc_Norm")["MARCA"].to_dict() if "MARCA" in df_bateu.columns else {}
        descricoes_bateu = set(df_bateu["Desc_Norm"].unique())
    except Exception:
        dict_bateu_ind, dict_bateu_mar, descricoes_bateu = {}, {}, set()
        warnings.append("Aba 'BateuLevou' indisponível; campanhas podem ficar incompletas.")

    try:
        df = pd.read_excel(
            planilha_path, sheet_name="Banco_Dados_Semanal", skiprows=5, header=None, engine="openpyxl"
        )
        required_idx = [0, 1, 2, 5, 7, 9, 11]
        missing_idx = [idx for idx in required_idx if idx not in df.columns]
        if missing_idx:
            warnings.append(f"Banco_Dados_Semanal sem colunas esperadas: {missing_idx}.")
            return pd.DataFrame(), curva_abc_codigos, warnings, "ESTRUTURA_BANCO_DADOS_INVALIDA"

        coluna_b_original = df[1].copy()
        cat_raw = df[1].astype(str)
        mask_categoria = cat_raw.str.match(r"^\s*\d{1,3}\s*-\s*.+")
        df["Categoria"] = cat_raw.where(mask_categoria, other=None).ffill().apply(_manter_categoria_completa)
        df["Categoria"] = df["Categoria"].replace("", "Sem Categoria").fillna("Sem Categoria")

        df["Código"] = df[0].astype(str)
        df["Descrição"] = df[2].astype(str).str.strip("* ")
        df["Preço_7"] = pd.to_numeric(df[5], errors="coerce")
        df["Preço_14"] = pd.to_numeric(df[7], errors="coerce")
        df["Preço_21"] = pd.to_numeric(df[9], errors="coerce")
        df["Preço_28"] = pd.to_numeric(df[11], errors="coerce")
        df["ST_Flag"] = df.get(12, pd.Series(index=df.index, dtype="object")).fillna("").astype(str).str.strip()

        df = df.dropna(subset=["Preço_7"])
        df = df[
            (df["Preço_7"] > 0)
            & (df["Descrição"].str.strip().str.lower() != "nan")
            & (df["Descrição"].str.strip() != "")
        ]

        df["Desc_Norm"] = df["Descrição"].apply(lambda x: re.sub(r"\s+", " ", str(x).strip().upper()))
        df["Camp_Bateu"] = df["Desc_Norm"].isin(descricoes_bateu)

        if lista_industrias:
            industria_fallback = pd.Series(
                df.apply(
                    lambda row: lista_industrias[
                        _deterministic_index_from_key(
                            f"{row.get('Código', '')}|{row.get('Desc_Norm', '')}", len(lista_industrias)
                        )
                    ],
                    axis=1,
                ),
                index=df.index,
            )
        else:
            industria_fallback = pd.Series("Sem Indústria", index=df.index)

        df["Indústria"] = df["Desc_Norm"].map(dict_bateu_ind).fillna(industria_fallback)
        df["Marca_BL"] = df["Desc_Norm"].map(dict_bateu_mar)
        mask_missing = df["Marca_BL"].isna() | (df["Marca_BL"] == "")
        df["Marca"] = df["Marca_BL"]
        if mask_missing.any():
            df.loc[mask_missing, "Marca"] = df.loc[mask_missing, "Desc_Norm"].apply(achar_marca)

        df["Fator_Anterior"] = df.apply(
            lambda row: _deterministic_fator_anterior(f"{row.get('Código', '')}|{row.get('Desc_Norm', '')}"), axis=1
        )

        curva_abc_set = set(curva_abc_codigos)
        df["Curva_ABC"] = df["Código"].apply(
            lambda cod: re.sub(r"\D", "", str(cod).split("-")[0]) in curva_abc_set
        )

        def checar_meta_mensal(row):
            desc = str(row.get("Desc_Norm", "")).upper()
            marca = str(row.get("Marca", "")).upper()
            cat = str(row.get("Categoria", "")).upper()
            if "ESCOLA" in cat or "PAPELARIA" in cat:
                return True
            if "INSETICIDA" in cat or "INSETICIDA" in desc:
                return True
            if "FOLHALEV" in marca or "FOLHA LEV" in marca:
                return True
            if "BABYSEC" in marca or "BABY SEC" in marca:
                return True
            if "CHAMEX" in marca or "CHAMEX" in desc:
                return True
            if "CHAMEQUINHO" in marca or "CHAMEQUINHO" in desc:
                return True
            if ("LIMAO" in marca or "LIMÃO" in marca) and ("LIXO" in desc or "SACO" in desc):
                return True
            if "LIMAO" in desc and "LIXO" in desc:
                return True
            if "NETZ" in marca and ("LIXO" in desc or "SACO" in desc):
                return True
            if "NETZ" in desc and "LIXO" in desc:
                return True
            return False

        df["Meta_Mensal"] = df.apply(checar_meta_mensal, axis=1)

        codigos_podendo_exatos, codigos_podendo_parciais = set(), set()
        try:
            df_podendo = pd.read_excel(planilha_path, sheet_name="TO PODENDO", header=None, engine="openpyxl")
            for col in df_podendo.columns:
                for val in df_podendo[col].dropna():
                    val_str = str(val).strip().upper()
                    if "E+" in val_str:
                        raiz = re.sub(r"\D", "", val_str.split("E")[0])
                        if len(raiz) >= 4:
                            codigos_podendo_parciais.add(raiz)
                    else:
                        v_num = re.sub(r"\D", "", val_str)
                        if len(v_num) >= 4:
                            codigos_podendo_exatos.add(v_num)
        except Exception:
            warnings.append("Aba 'TO PODENDO' indisponível; usando fallback por descrição.")

        def cruzar_ean_podendo(idx):
            val_b = re.sub(r"\D", "", str(coluna_b_original.get(idx, "")))
            val_a = re.sub(r"\D", "", str(df.at[idx, "Código"]))
            if val_b and val_b in codigos_podendo_exatos:
                return True
            if val_a and val_a in codigos_podendo_exatos:
                return True
            for parcial in codigos_podendo_parciais:
                if val_b and val_b.startswith(parcial):
                    return True
                if val_a and val_a.startswith(parcial):
                    return True
            return False

        df["Camp_ToPodendo"] = [cruzar_ean_podendo(idx) for idx in df.index]
        if not df["Camp_ToPodendo"].any():
            marcas_podendo = ["KINDER", "MAGGI", "GAROTO", "NESTLE", "SUFRESH", "TODDY", "NESCAU"]
            df["Camp_ToPodendo"] = df["Desc_Norm"].apply(lambda desc: any(m in desc for m in marcas_podendo))

        codigos_colgate_exatos, codigos_colgate_parciais = set(), set()
        try:
            df_colgate = pd.read_excel(planilha_path, sheet_name="COLGATE", header=None, engine="openpyxl")
            for col in df_colgate.columns:
                for val in df_colgate[col].dropna():
                    val_str = str(val).strip().upper()
                    if "E+" in val_str:
                        raiz = re.sub(r"\D", "", val_str.split("E")[0])
                        if len(raiz) >= 4:
                            codigos_colgate_parciais.add(raiz)
                    else:
                        v_num = re.sub(r"\D", "", val_str)
                        if len(v_num) >= 4:
                            codigos_colgate_exatos.add(v_num)
        except Exception:
            warnings.append("Aba 'COLGATE' indisponível; usando fallback por descrição.")

        def cruzar_ean_colgate(idx):
            val_b = re.sub(r"\D", "", str(coluna_b_original.get(idx, "")))
            val_a = re.sub(r"\D", "", str(df.at[idx, "Código"]))
            if val_b and val_b in codigos_colgate_exatos:
                return True
            if val_a and val_a in codigos_colgate_exatos:
                return True
            for parcial in codigos_colgate_parciais:
                if val_b and val_b.startswith(parcial):
                    return True
                if val_a and val_a.startswith(parcial):
                    return True
            return False

        df["Camp_Colgate"] = [cruzar_ean_colgate(idx) for idx in df.index]
        if not df["Camp_Colgate"].any():
            marcas_colgate = ["COLGATE", "SORRISO", "PROTEX", "PALMOLIVE", "AJAX", "PINHO SOL"]
            df["Camp_Colgate"] = df["Desc_Norm"].apply(lambda desc: any(m in desc for m in marcas_colgate))

        missing_output = [c for c in EXPECTED_OUTPUT_COLUMNS if c not in df.columns]
        if missing_output:
            warnings.append(f"Colunas finais ausentes após processamento: {missing_output}.")

        return df, curva_abc_codigos, warnings, ""

    except Exception as exc:
        logger.exception("Erro ao carregar/processar dados da planilha: %s", exc)
        return pd.DataFrame(), curva_abc_codigos, warnings, "ERRO_PROCESSAMENTO_PLANILHA"
