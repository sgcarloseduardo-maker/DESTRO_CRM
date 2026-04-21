import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from src.config.paths import domain_dirs
from src.utils.fs_ops import atomic_copy, safe_copy_if_exists
from src.utils.time_ops import compact_timestamp


@dataclass
class PromotionResult:
    domain: str
    promoted_to: str
    moved_previous: bool
    archived_current: bool
    rollback: bool
    had_previous_current: bool
    restored_state: str


def promote_transactional(domain: str, incoming_file: Path, dry_run: bool = False, force_fail: bool = False) -> PromotionResult:
    dirs: Dict[str, Path] = domain_dirs(domain)
    atual = dirs["atual"] / incoming_file.name
    anterior = dirs["anterior"] / incoming_file.name
    historico = dirs["historico"] / f"{compact_timestamp()}__{incoming_file.name}"

    moved_previous = False
    archived_current = False
    had_previous_current = atual.exists()

    if dry_run:
        return PromotionResult(domain, str(atual), moved_previous, archived_current, rollback=False, had_previous_current=had_previous_current, restored_state="dry_run")

    snapshot_dir = dirs["base"] / "_snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snap_atual = snapshot_dir / incoming_file.name
    safe_copy_if_exists(atual, snap_atual)

    try:
        if atual.exists():
            atomic_copy(atual, historico)
            archived_current = True
            atomic_copy(atual, anterior)
            moved_previous = True

        if force_fail:
            raise RuntimeError("Falha controlada durante promoção transacional.")

        atomic_copy(incoming_file, atual)
        return PromotionResult(
            domain,
            str(atual),
            moved_previous,
            archived_current,
            rollback=False,
            had_previous_current=had_previous_current,
            restored_state="not_required",
        )
    except Exception:
        if snap_atual.exists():
            atomic_copy(snap_atual, atual)
            restored_state = "restored_from_snapshot"
        elif atual.exists():
            atual.unlink(missing_ok=True)
            restored_state = "removed_partial_current"
        else:
            restored_state = "kept_without_current"
        return PromotionResult(
            domain,
            str(atual),
            moved_previous,
            archived_current,
            rollback=True,
            had_previous_current=had_previous_current,
            restored_state=restored_state,
        )
    finally:
        shutil.rmtree(snapshot_dir, ignore_errors=True)
