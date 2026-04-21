from pathlib import Path

import pandas as pd


def read_excel_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name, dtype=str)


def read_excel_all(path: Path) -> dict:
    xls = pd.ExcelFile(path)
    return {sheet: pd.read_excel(path, sheet_name=sheet, dtype=str) for sheet in xls.sheet_names}
