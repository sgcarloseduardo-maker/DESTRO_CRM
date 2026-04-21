from pathlib import Path
from typing import Any, Dict

import pandas as pd

from src.config.paths import REJECTS_DIR, ensure_runtime_dirs
from src.config.schema_contract import CONTRACTS, SCHEMA_VERSION
from src.data.file_classifier import classify_excel_by_content
from src.data.normalizers import normalize_abc, normalize_campanhas, normalize_semanal
from src.data.readers import read_excel_sheet
from src.services.curation_service import curate_outputs
from src.services.promotion_service import promote_transactional
from src.services.staging_service import write_staging
from src.utils.hash_ops import sha256_file
from src.utils.log_ops import append_log, dump_json_report
from src.utils.time_ops import compact_timestamp


NORMALIZERS = {
    "semanal": normalize_semanal,
    "abc": normalize_abc,
    "campanhas": normalize_campanhas,
}


def _save_reject(file_path: Path, reason: str, dry_run: bool) -> str:
    name = f"{compact_timestamp()}__{reason}__{file_path.name}"
    out = REJECTS_DIR / name
    if not dry_run:
        REJECTS_DIR.mkdir(parents=True, exist_ok=True)
        out.write_bytes(file_path.read_bytes())
    return str(out)


def process_upload(
    file_path: str,
    user: str,
    dry_run: bool = False,
    confirm_intermediate: bool = False,
    force_fail_promotion: bool = False,
) -> Dict[str, Any]:
    ensure_runtime_dirs()
    src = Path(file_path)
    report: Dict[str, Any] = {
        "file": str(src),
        "dry_run": dry_run,
        "user": user,
        "schema_version": SCHEMA_VERSION,
        "warnings": [],
        "would_change_files": [],
        "reject_path": "",
    }

    if not src.exists():
        report["decision"] = "rejected"
        report["reason"] = "arquivo_nao_existe"
        return report

    file_hash = sha256_file(src)
    report["sha256"] = file_hash

    try:
        cls = classify_excel_by_content(src)
    except Exception as exc:
        report["decision"] = "rejected"
        report["reason"] = f"classificacao_falhou: {exc}"
        report["reject_path"] = _save_reject(src, "classificacao_falhou", dry_run)
        append_log(
            "upload_rejected",
            {"user": user, "sha256": file_hash, "reason": report["reason"], "reject_path": report["reject_path"]},
        )
        return report

    report["detected_type"] = cls.file_type
    report["scores"] = cls.sheet_scores
    report["winning_sheet"] = cls.selected_sheet
    report["confidence"] = cls.confidence
    report["confidence_band"] = cls.confidence_band
    report["warnings"].extend(cls.warnings)

    if cls.confidence_band == "reject":
        report["decision"] = "rejected"
        report["reason"] = "confidence_low"
        report["reject_path"] = _save_reject(src, "confidence_low", dry_run)
        append_log(
            "upload_rejected",
            {"user": user, "sha256": file_hash, "reason": report["reason"], "reject_path": report["reject_path"]},
        )
        return report

    if cls.confidence_band == "confirm" and not confirm_intermediate:
        report["decision"] = "needs_confirmation"
        report["reason"] = "confidence_intermediate"
        append_log(
            "upload_pending_confirmation",
            {"user": user, "sha256": file_hash, "detected_type": cls.file_type, "confidence": cls.confidence},
        )
        return report

    df_raw = read_excel_sheet(src, cls.selected_sheet)
    normalizer = NORMALIZERS[cls.file_type]
    normalized_df, mapped_cols, norm_warnings = normalizer(df_raw)
    report["mapped_columns"] = mapped_cols
    report["warnings"].extend(norm_warnings)

    missing_required = [c for c in CONTRACTS[cls.file_type].required_columns if c not in normalized_df.columns]
    if missing_required:
        report["decision"] = "rejected"
        report["reason"] = f"schema_invalido:{','.join(missing_required)}"
        report["reject_path"] = _save_reject(src, "schema_invalido", dry_run)
        append_log(
            "upload_rejected",
            {"user": user, "sha256": file_hash, "reason": report["reason"], "reject_path": report["reject_path"]},
        )
        return report

    promotion = promote_transactional(
        cls.file_type,
        src,
        dry_run=dry_run,
        force_fail=force_fail_promotion,
    )
    report["promotion"] = promotion.__dict__

    if promotion.rollback:
        report["decision"] = "failed_with_rollback"
        report["reason"] = "promotion_failed_rollback_applied"
        append_log(
            "upload_processed",
            {
                "user": user,
                "sha256": file_hash,
                "detected_type": cls.file_type,
                "confidence": cls.confidence,
                "decision": report["decision"],
                "rollback": True,
                "dry_run": dry_run,
            },
        )
        report_path = dump_json_report("upload_report", report)
        report["report_file"] = str(report_path)
        return report

    staging_path, metadata = write_staging(cls.file_type, normalized_df, src, dry_run=dry_run)
    report["staging"] = {"path": str(staging_path), **metadata}
    report["would_change_files"].append(str(staging_path))

    if cls.file_type == "semanal":
        prev_name = f"{cls.file_type}_anterior_staging.parquet"
        previous_df = pd.DataFrame(columns=["codigo_destro", "preco_7"])
        anterior_file = Path(promotion.promoted_to).parent.parent / "anterior" / src.name
        if anterior_file.exists():
            df_prev_raw = read_excel_sheet(anterior_file, cls.selected_sheet)
            previous_df, _, _ = normalize_semanal(df_prev_raw)
        if not dry_run:
            from src.config.paths import STAGING_DIR

            previous_df.to_parquet(STAGING_DIR / prev_name, index=False)
        report["would_change_files"].append(str(Path("data/staging") / prev_name))

    curated = curate_outputs(dry_run=dry_run)
    report["curated_outputs"] = curated
    report["would_change_files"].extend(curated.values())

    report["decision"] = "accepted_dry_run" if dry_run else "accepted"
    report["reason"] = "ok"

    append_log(
        "upload_processed",
        {
            "user": user,
            "sha256": file_hash,
            "detected_type": cls.file_type,
            "confidence": cls.confidence,
            "decision": report["decision"],
            "rollback": promotion.rollback,
            "dry_run": dry_run,
        },
    )
    report_path = dump_json_report("dry_run_report" if dry_run else "upload_report", report)
    report["report_file"] = str(report_path)
    return report
