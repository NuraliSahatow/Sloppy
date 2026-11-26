"""Every script under scripts/ finds the repo root, not scripts/ (2026-11-25: build_creep_abilities.py after the
move to scripts/gen read scripts/data and quietly wrote nothing; four more scripts moved the same way still pointed
one level short: lift_old_desc read scripts/data, the three gothic-icon generators wrote to scripts/icons/).

Read, not run: each module-level `ROOT = ...__file__...` (ROOT / _ROOT / REPO_ROOT / HERE / _HERE) is evaluated with
the script's own __file__. A *ROOT name must be the repo; a *HERE name the repo or the script's own folder (the
terrain scripts keep _HERE for their sibling imports)."""
import ast
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ROOT_NAMES = {"ROOT", "_ROOT", "REPO_ROOT"}
HERE_NAMES = {"HERE", "_HERE"}


def _scripts():
    return sorted(p for p in (REPO / "scripts").rglob("*.py") if "__pycache__" not in p.parts)


def _roots(path, text=None):
    """{name: (resolved folder, source)} for the module-level root assignments of one script."""
    text = path.read_text(encoding="utf-8") if text is None else text
    tree = ast.parse(text)
    ns = {"os": os, "Path": Path, "_os": os, "__file__": str(path)}
    out = {}
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            continue
        name = node.targets[0].id
        if name not in ROOT_NAMES | HERE_NAMES:
            continue
        src = ast.get_source_segment(text, node.value)
        try:
            value = eval(compile(ast.Expression(node.value), str(path), "eval"), ns)   # noqa: S307 - os.path / Path only
        except Exception:
            continue    # built from something this test does not model: not its business
        ns[name] = value
        out[name] = (Path(os.path.normpath(str(value))).resolve(), src)
    return out


@pytest.mark.parametrize("path", _scripts(), ids=lambda p: p.relative_to(REPO).as_posix())
def test_script_root_is_the_repo(path):
    for name, (folder, src) in _roots(path).items():
        allowed = {REPO} if name in ROOT_NAMES else {REPO, path.parent.resolve()}
        assert folder in allowed, (f"{name} = {src} resolves to {folder.relative_to(REPO).as_posix() or '.'}/, "
                                   f"not the repo root")


def test_the_guard_sees_a_short_root():
    """The 2026-11-25 mistake, as text: scripts/gen/ with parents[1] lands on scripts/ (the guard is not blind)."""
    probe = REPO / "scripts" / "gen" / "probe.py"
    roots = _roots(probe, "from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n")
    assert roots["ROOT"][0] == (REPO / "scripts").resolve()
