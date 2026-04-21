from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


AUTO_CONFIDENCE = 0.80
CONFIRM_CONFIDENCE = 0.65


KEYWORDS: Dict[str, List[str]] = {
    "semanal": ["preco", "preço", "estoque", "descricao", "produto", "codigo", "ean"],
    "abc": ["curva", "abc", "classificacao", "classificação", "tante"],
    "campanhas": ["campanha", "bateulevou", "to podendo", "colgate", "flag"],
}

HEADER_HINTS: Dict[str, List[str]] = {
    "semanal": ["codigo", "barras", "descricao", "emb", "vista", "14 dias", "21 dias", "28 dias", "s.t"],
    "abc": ["tante", "curva abc", "abc"],
    "campanhas": ["industria", "marca", "campanha", "produto", "ean"],
}


@dataclass
class ClassificationResult:
    file_type: str
    confidence: float
    confidence_band: str
    selected_sheet: str
    sheet_scores: Dict[str, float]
    warnings: List[str]


def _score_sheet(df: pd.DataFrame, target_type: str) -> float:
    cols = [str(c).strip().lower() for c in df.columns]
    cell_text = " ".join(cols)
    header_hits = sum(1 for h in HEADER_HINTS[target_type] if any(h in c for c in cols))
    header_score = header_hits / max(len(HEADER_HINTS[target_type]), 1)

    if not df.empty:
        sample = df.head(30).fillna("").astype(str)
        cell_text += " " + " ".join(sample.to_numpy().ravel().tolist()).lower()
    keyword_hits = sum(1 for k in KEYWORDS[target_type] if k in cell_text)
    keyword_score = keyword_hits / max(len(KEYWORDS[target_type]), 1)

    penalty = 0.0
    if target_type == "semanal" and "curva abc" in cell_text:
        penalty += 0.2
    if target_type == "abc" and "14 dias" in cell_text:
        penalty += 0.15

    return max(0.0, (header_score * 0.65) + (keyword_score * 0.35) - penalty)


def classify_excel_by_content(path: Path) -> ClassificationResult:
    warnings: List[str] = []
    xls = pd.ExcelFile(path)
    if not xls.sheet_names:
        raise ValueError("Arquivo sem abas para classificar.")

    per_type_best: Dict[str, Tuple[str, float]] = {}
    flat_sheet_scores: Dict[str, float] = {}

    for target in KEYWORDS:
        best_sheet = ""
        best_score = 0.0
        for sheet in xls.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet, dtype=str)
            score = _score_sheet(df, target)
            flat_sheet_scores[f"{target}:{sheet}"] = round(score, 4)
            if score > best_score:
                best_score = score
                best_sheet = sheet
        per_type_best[target] = (best_sheet, best_score)

    winner_type = max(per_type_best.keys(), key=lambda k: per_type_best[k][1])
    winner_sheet, winner_score = per_type_best[winner_type]

    if winner_score >= AUTO_CONFIDENCE:
        band = "auto"
    elif winner_score >= CONFIRM_CONFIDENCE:
        band = "confirm"
        warnings.append("Classificação em banda intermediária: exige confirmação na UI.")
    else:
        band = "reject"
        warnings.append("Classificação em banda baixa: arquivo deve ser rejeitado.")

    return ClassificationResult(
        file_type=winner_type,
        confidence=round(winner_score, 4),
        confidence_band=band,
        selected_sheet=winner_sheet,
        sheet_scores=flat_sheet_scores,
        warnings=warnings,
    )
