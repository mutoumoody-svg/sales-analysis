"""Zero-dependency fallback runner for simple test functions.

Use pytest in normal development. This runner keeps the core rule suite usable
in restricted deployment environments where test packages cannot be installed.
"""

import importlib.util
import inspect
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


class MonkeyPatch:
    def __init__(self):
        self._changes = []

    def setattr(self, obj, name, value):
        self._changes.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def undo(self):
        for obj, name, old in reversed(self._changes):
            setattr(obj, name, old)


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    passed = failed = 0
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        module = load_module(path)
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            patch = MonkeyPatch()
            try:
                kwargs = {"monkeypatch": patch} if "monkeypatch" in inspect.signature(fn).parameters else {}
                fn(**kwargs)
                passed += 1
                print(f"PASS {path.name}::{name}")
            except Exception as exc:
                failed += 1
                print(f"FAIL {path.name}::{name}: {exc}")
            finally:
                patch.undo()
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
