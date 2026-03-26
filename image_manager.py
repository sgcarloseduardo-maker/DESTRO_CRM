import hashlib
import json
import os
import re
from datetime import datetime
from typing import Dict, Tuple


METADATA_FILE = "image_metadata.json"


def normalize_product_code(codigo: str) -> str:
    return re.sub(r"\D", "", str(codigo or ""))


def metadata_path(base_dir: str) -> str:
    return os.path.join(base_dir, "Base de Imagens", METADATA_FILE)


def load_metadata(base_dir: str) -> Dict:
    path = metadata_path(base_dir)
    if not os.path.exists(path):
        return {"images": {}, "updated_at": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"images": {}, "updated_at": None}
            data.setdefault("images", {})
            data.setdefault("updated_at", None)
            return data
    except Exception:
        return {"images": {}, "updated_at": None}


def save_metadata(base_dir: str, metadata: Dict) -> None:
    os.makedirs(os.path.join(base_dir, "Base de Imagens"), exist_ok=True)
    metadata["updated_at"] = datetime.now().isoformat()
    with open(metadata_path(base_dir), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def build_image_index(base_dir: str) -> Tuple[Dict[str, str], Dict]:
    pasta_imagens = os.path.join(base_dir, "Base de Imagens")
    idx: Dict[str, str] = {}
    if not os.path.exists(pasta_imagens):
        return idx, load_metadata(base_dir)

    for root, _, files in os.walk(pasta_imagens):
        for fn in files:
            if fn == METADATA_FILE:
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".webp"):
                num = normalize_product_code(os.path.splitext(fn)[0])
                if num:
                    idx[num] = os.path.join(root, fn)
    return idx, load_metadata(base_dir)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def store_product_image(
    base_dir: str,
    uploaded_file,
    code: str,
    allowed_exts,
    max_mb: int,
    min_code_len: int = 4,
    max_code_len: int = 14,
) -> Tuple[bool, str, Dict]:
    if uploaded_file is None:
        return False, "Nenhum arquivo enviado.", {}

    code_norm = normalize_product_code(code)
    if not code_norm:
        return False, "Código do produto inválido. Use apenas números.", {}
    if len(code_norm) < min_code_len or len(code_norm) > max_code_len:
        return False, f"Código inválido: esperado entre {min_code_len} e {max_code_len} dígitos.", {}

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in allowed_exts:
        return False, f"Formato inválido. Permitidos: {', '.join(sorted(allowed_exts))}.", {}

    size_bytes = getattr(uploaded_file, "size", None)
    if size_bytes is not None and size_bytes > max_mb * 1024 * 1024:
        return False, f"Arquivo muito grande. Limite: {max_mb} MB.", {}

    content = uploaded_file.getbuffer()
    img_hash = _sha256_bytes(content)

    pasta_imagens = os.path.join(base_dir, "Base de Imagens")
    os.makedirs(pasta_imagens, exist_ok=True)
    backups_dir = os.path.join(pasta_imagens, "_backup")
    os.makedirs(backups_dir, exist_ok=True)

    metadata = load_metadata(base_dir)
    idx, _ = build_image_index(base_dir)
    old_path = idx.get(code_norm)
    backup_path = ""

    if old_path and os.path.exists(old_path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{code_norm}_{ts}{os.path.splitext(old_path)[1].lower()}"
        backup_path = os.path.join(backups_dir, backup_name)
        os.replace(old_path, backup_path)

    new_name = f"{code_norm}{ext}"
    new_path = os.path.join(pasta_imagens, new_name)
    with open(new_path, "wb") as f:
        f.write(content)

    metadata["images"][code_norm] = {
        "code": code_norm,
        "file_name": new_name,
        "original_name": uploaded_file.name,
        "hash_sha256": img_hash,
        "uploaded_at": datetime.now().isoformat(),
        "size_bytes": len(content),
        "replaced_previous": bool(old_path),
        "backup_path": backup_path,
    }
    save_metadata(base_dir, metadata)
    return True, "Imagem salva com sucesso.", metadata["images"][code_norm]
