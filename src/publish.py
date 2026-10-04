"""Publish a staged batch, restoring targets on ordinary replacement failures.

Not crash/power-loss safe or atomic to concurrent readers. Callers must stage the
whole batch before calling, on the same filesystem as each respective target.
"""
import shutil
import tempfile
from pathlib import Path


def publish_files(pairs):
    """Consume (staged Path, target Path) pairs; preserve backups if rollback fails."""
    pairs = [(Path(stage), Path(target)) for stage, target in pairs]
    targets = [target.resolve() for _, target in pairs]
    if len(set(targets)) != len(targets):
        raise ValueError("publication targets must be unique")
    for stage, target in pairs:
        if not stage.is_file():
            raise FileNotFoundError(f"staged file missing: {stage}")
        if stage.resolve() in targets:
            raise ValueError(f"staged file is also a target: {stage}")
        if target.exists() and not target.is_file():
            raise IsADirectoryError(f"target is not a file: {target}")
        if not target.parent.is_dir():
            raise FileNotFoundError(f"target directory missing: {target.parent}")

    backups = {}
    promoted = []
    rollback_failed = False
    try:
        # Copy every original before promoting any file; absent originals stay absent.
        for _, target in pairs:
            if target.exists():
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", suffix=".bak", delete=False) as backup:
                    backups[target] = Path(backup.name)
                shutil.copy2(target, backups[target])
        for stage, target in pairs:
            stage.replace(target)
            promoted.append(target)
    except Exception as publication_error:
        errors = []
        for target in reversed(promoted):
            try:
                if target in backups:
                    backups[target].replace(target)
                else:
                    target.unlink(missing_ok=True)
            except Exception as rollback_error:
                errors.append(f"{target}: {rollback_error}")
        if errors:
            rollback_failed = True
            retained = [str(path) for path in backups.values() if path.exists()]
            raise RuntimeError(f"publication failed; rollback failed: {errors}; retained backups: {retained}") from publication_error
        raise
    finally:
        if not rollback_failed:
            for backup in backups.values():
                try:
                    backup.unlink(missing_ok=True)
                except OSError:
                    pass  # A leftover backup must not turn a successful publish into a failure.
