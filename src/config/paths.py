from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"

INPUT_DIR = DATA_DIR / "input"
STAGING_DIR = DATA_DIR / "staging"
CURATED_DIR = DATA_DIR / "curated"
LOG_DIR = DATA_DIR / "logs" / "cargas"
REJECTS_DIR = DATA_DIR / "rejects" / "arquivos_invalidos"


def domain_dirs(domain: str) -> dict:
    base = INPUT_DIR / domain
    return {
        "base": base,
        "atual": base / "atual",
        "anterior": base / "anterior",
        "historico": base / "historico",
    }


def ensure_runtime_dirs() -> None:
    for d in [INPUT_DIR, STAGING_DIR, CURATED_DIR, LOG_DIR, REJECTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    for name in ["semanal", "abc", "campanhas"]:
        dirs = domain_dirs(name)
        for p in dirs.values():
            p.mkdir(parents=True, exist_ok=True)
