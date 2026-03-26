import pandas as pd

from core_utils import normalize_numeric_value, preparar_df_app, validate_upload_basic


class DummyUpload:
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size


def test_validate_upload_basic_ok():
    file = DummyUpload("foto.jpg", 1024)
    ok, msg = validate_upload_basic(file, {".jpg", ".png"}, 5, "imagem")
    assert ok is True
    assert msg == ""


def test_validate_upload_basic_invalid_extension():
    file = DummyUpload("foto.gif", 1024)
    ok, msg = validate_upload_basic(file, {".jpg", ".png"}, 5, "imagem")
    assert ok is False
    assert "Formato inválido" in msg


def test_validate_upload_basic_file_too_large():
    file = DummyUpload("foto.jpg", 6 * 1024 * 1024)
    ok, msg = validate_upload_basic(file, {".jpg", ".png"}, 5, "imagem")
    assert ok is False
    assert "Arquivo muito grande" in msg


def test_normalize_numeric_value_bounds_and_fallback():
    assert normalize_numeric_value("10.5", min_value=0, max_value=20) == 10.5
    assert normalize_numeric_value("abc", fallback=3.0) == 3.0
    assert normalize_numeric_value(float("inf"), fallback=2.0) == 2.0
    assert normalize_numeric_value(-5, min_value=0) == 0
    assert normalize_numeric_value(150, max_value=100) == 100


def test_preparar_df_app_happy_path():
    df = pd.DataFrame(
        [
            {"Preço_7": 10.0, "Preço_14": 12.0, "Preço_21": 12.0, "Preço_28": 12.0, "Fator_Anterior": 1.2},
            {"Preço_7": 12.0, "Preço_14": 10.0, "Preço_21": 10.0, "Preço_28": 10.0, "Fator_Anterior": 0.8},
            {"Preço_7": 10.0, "Preço_14": 10.0, "Preço_21": 10.0, "Preço_28": 10.0, "Fator_Anterior": 1.0},
        ]
    )
    out = preparar_df_app(df, "Preço_7")
    assert "Status" in out.columns
    assert out.loc[0, "Status"].startswith("🟢")
    assert out.loc[1, "Status"].startswith("🔴")
    assert out.loc[2, "Status"].startswith("⚫")


def test_preparar_df_app_invalid_prazo_fallback():
    df = pd.DataFrame([{"Preço_7": 10.0, "Preço_14": 11.0, "Preço_21": 12.0, "Preço_28": 13.0, "Fator_Anterior": 1.0}])
    out = preparar_df_app(df, "PRAZO_INVALIDO")
    assert out.loc[0, "Preço Atual"] == 10.0
