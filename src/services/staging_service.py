from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from src.config.paths import STAGING_DIR


def write_staging(domain: str, normalized_df: pd.DataFrame, source_file: Path, dry_run: bool = False) -> Tuple[Path, Dict[str, str]]:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    path = STAGING_DIR / f"{domain}_staging.parquet"
    metadata = {
        "domain": domain,
        "rows": str(len(normalized_df)),
        "source_file": str(source_file),
    }
    if not dry_run:
        normalized_df.to_parquet(path, index=False)
    return path, metadata


def read_staging(domain: str) -> pd.DataFrame:
    path = STAGING_DIR / f"{domain}_staging.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)
