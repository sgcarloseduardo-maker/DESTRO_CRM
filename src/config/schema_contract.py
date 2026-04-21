from dataclasses import dataclass
from typing import Dict, List, Tuple


SCHEMA_VERSION = "v1.0.0"


CONFIDENCE_BANDS: Tuple[str, ...] = ("auto", "confirm", "reject")
CURVA_ABC_ENUM: Tuple[str, ...] = ("A", "B", "C")
ESTOQUE_STATUS_ENUM: Tuple[str, ...] = ("EM_ESTOQUE", "SEM_ESTOQUE")
COMPARATIVO_TENDENCIA_ENUM: Tuple[str, ...] = (
    "SUBIU",
    "CAIU",
    "ESTAVEL",
    "NOVO",
    "SEM_BASE",
)


@dataclass(frozen=True)
class DomainContract:
    domain: str
    required_columns: List[str]
    optional_columns: List[str]
    canonical_map: Dict[str, str]


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    path: str
    required_columns: List[str]
    derived_columns: List[str]
    enums: Dict[str, Tuple[str, ...]]


SEMANAL_CONTRACT = DomainContract(
    domain="semanal",
    required_columns=[
        "codigo_destro",
        "descricao_produto",
        "preco_7",
        "preco_14",
        "preco_21",
        "preco_28",
        "estoque_atual",
    ],
    optional_columns=["ean", "industria", "marca", "categoria", "st_flag"],
    canonical_map={
        "codigo": "codigo_destro",
        "código": "codigo_destro",
        "codigo_destro": "codigo_destro",
        "cod": "codigo_destro",
        "descricao": "descricao_produto",
        "descrição": "descricao_produto",
        "descricao do produto": "descricao_produto",
        "produto": "descricao_produto",
        "preco_7": "preco_7",
        "preço_7": "preco_7",
        "a vista": "preco_7",
        "preco_14": "preco_14",
        "preco_21": "preco_21",
        "preco_28": "preco_28",
        "estoque": "estoque_atual",
        "estoque_atual": "estoque_atual",
        "ean": "ean",
        "industria": "industria",
        "marca": "marca",
        "categoria": "categoria",
        "st_flag": "st_flag",
    },
)


ABC_CONTRACT = DomainContract(
    domain="abc",
    required_columns=["codigo_destro", "curva_abc"],
    optional_columns=["descricao_produto"],
    canonical_map={
        "codigo": "codigo_destro",
        "código": "codigo_destro",
        "codigo_destro": "codigo_destro",
        "curva": "curva_abc",
        "curva_abc": "curva_abc",
        "abc": "curva_abc",
        "descricao": "descricao_produto",
        "descrição": "descricao_produto",
    },
)


CAMPANHAS_CONTRACT = DomainContract(
    domain="campanhas",
    required_columns=["codigo_destro", "flag_campanha"],
    optional_columns=["descricao_produto", "nome_campanha"],
    canonical_map={
        "codigo": "codigo_destro",
        "código": "codigo_destro",
        "codigo_destro": "codigo_destro",
        "descricao": "descricao_produto",
        "descrição": "descricao_produto",
        "campanha": "nome_campanha",
        "nome_campanha": "nome_campanha",
        "flag": "flag_campanha",
        "flag_campanha": "flag_campanha",
    },
)


CONTRACTS = {
    "semanal": SEMANAL_CONTRACT,
    "abc": ABC_CONTRACT,
    "campanhas": CAMPANHAS_CONTRACT,
}


DATASETS = {
    "semanal_staging": DatasetSpec(
        name="semanal_staging",
        path="data/staging/semanal_staging.parquet",
        required_columns=SEMANAL_CONTRACT.required_columns + SEMANAL_CONTRACT.optional_columns,
        derived_columns=[],
        enums={},
    ),
    "abc_staging": DatasetSpec(
        name="abc_staging",
        path="data/staging/abc_staging.parquet",
        required_columns=ABC_CONTRACT.required_columns + ABC_CONTRACT.optional_columns,
        derived_columns=[],
        enums={"curva_abc": CURVA_ABC_ENUM},
    ),
    "campanhas_staging": DatasetSpec(
        name="campanhas_staging",
        path="data/staging/campanhas_staging.parquet",
        required_columns=CAMPANHAS_CONTRACT.required_columns + CAMPANHAS_CONTRACT.optional_columns,
        derived_columns=[],
        enums={},
    ),
    "curated_produtos": DatasetSpec(
        name="curated_produtos",
        path="data/curated/produtos_curated.parquet",
        required_columns=[
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
            "curva_abc",
            "flag_campanha",
        ],
        derived_columns=[],
        enums={"curva_abc": CURVA_ABC_ENUM},
    ),
    "curated_comparativo_semanal": DatasetSpec(
        name="curated_comparativo_semanal",
        path="data/curated/comparativo_semanal.parquet",
        required_columns=["codigo_destro", "preco_7_atual", "preco_7_anterior", "variacao_pct", "tendencia_preco"],
        derived_columns=["tendencia_preco"],
        enums={"tendencia_preco": COMPARATIVO_TENDENCIA_ENUM},
    ),
    "curated_app_ready": DatasetSpec(
        name="curated_app_ready",
        path="data/curated/curated_app_ready.parquet",
        required_columns=[
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
        ],
        derived_columns=["preco_base", "preco_unitario_base", "status_estoque"],
        enums={"status_estoque": ESTOQUE_STATUS_ENUM, "curva_abc": CURVA_ABC_ENUM},
    ),
}
