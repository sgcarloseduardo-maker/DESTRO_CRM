from pathlib import Path
from typing import Dict

import pandas as pd

from src.config.paths import CURATED_DIR, STAGING_DIR
from src.services.comparison_service import build_weekly_comparison
from src.services.staging_service import read_staging


def curate_outputs(dry_run: bool = False) -> Dict[str, str]:
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    semanal = read_staging("semanal")
    abc = read_staging("abc")
    campanhas = read_staging("campanhas")

    weekly_prev_path = STAGING_DIR / "semanal_anterior_staging.parquet"
    semanal_anterior = pd.read_parquet(weekly_prev_path) if weekly_prev_path.exists() else pd.DataFrame(columns=["codigo_destro", "preco_7"])

    if semanal.empty:
        semanal = pd.DataFrame(
            columns=[
                "codigo_destro",
                "descricao_produto",
                "preco_7",
                "preco_14",
                "preco_21",
                "preco_28",
                "estoque_atual",
                "ean",
                "industria",
                "marca",
                "categoria",
                "st_flag",
            ]
        )

    curated_produtos = semanal.copy()
    if not abc.empty:
        curated_produtos = curated_produtos.merge(abc[["codigo_destro", "curva_abc"]], on="codigo_destro", how="left")
    else:
        curated_produtos["curva_abc"] = ""

    if not campanhas.empty:
        camp_agg = campanhas.groupby("codigo_destro", as_index=False)["flag_campanha"].max()
        curated_produtos = curated_produtos.merge(camp_agg, on="codigo_destro", how="left")
    else:
        curated_produtos["flag_campanha"] = False

    curated_produtos["flag_campanha"] = curated_produtos["flag_campanha"].fillna(False)
    curated_produtos["curva_abc"] = curated_produtos["curva_abc"].fillna("C").astype(str).str.upper().str[:1]
    curated_produtos["preco_7"] = pd.to_numeric(curated_produtos["preco_7"], errors="coerce").fillna(0.0)
    curated_produtos["preco_14"] = pd.to_numeric(curated_produtos["preco_14"], errors="coerce").fillna(0.0)
    curated_produtos["preco_21"] = pd.to_numeric(curated_produtos["preco_21"], errors="coerce").fillna(0.0)
    curated_produtos["preco_28"] = pd.to_numeric(curated_produtos["preco_28"], errors="coerce").fillna(0.0)
    curated_produtos["estoque_atual"] = pd.to_numeric(curated_produtos["estoque_atual"], errors="coerce").fillna(0.0)

    curated_app_ready = curated_produtos.copy()
    curated_app_ready["preco_base"] = curated_app_ready["preco_7"]
    curated_app_ready["embalagem_qtd"] = 1
    curated_app_ready["preco_unitario_base"] = curated_app_ready["preco_base"] / curated_app_ready["embalagem_qtd"]
    curated_app_ready["status_estoque"] = curated_app_ready["estoque_atual"].apply(
        lambda v: "EM_ESTOQUE" if float(v) > 0 else "SEM_ESTOQUE"
    )

    app_cols = [
        "codigo_destro",
        "descricao_produto",
        "ean",
        "preco_base",
        "preco_7",
        "preco_14",
        "preco_21",
        "preco_28",
        "embalagem_qtd",
        "preco_unitario_base",
        "estoque_atual",
        "status_estoque",
        "curva_abc",
        "flag_campanha",
        "industria",
        "marca",
        "categoria",
        "st_flag",
    ]
    curated_app_ready = curated_app_ready[app_cols].copy()

    comparativo = build_weekly_comparison(curated_produtos, semanal_anterior)

    out = {
        "curated_produtos": str(CURATED_DIR / "produtos_curated.parquet"),
        "curated_campanhas": str(CURATED_DIR / "campanhas_curated.parquet"),
        "curated_comparativo_semanal": str(CURATED_DIR / "comparativo_semanal.parquet"),
        "curated_app_ready": str(CURATED_DIR / "curated_app_ready.parquet"),
    }

    if not dry_run:
        curated_produtos.to_parquet(out["curated_produtos"], index=False)
        campanhas.to_parquet(out["curated_campanhas"], index=False)
        comparativo.to_parquet(out["curated_comparativo_semanal"], index=False)
        curated_app_ready.to_parquet(out["curated_app_ready"], index=False)
    return out
