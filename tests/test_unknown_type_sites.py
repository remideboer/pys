"""Fail-closed unknown types at field / param / return / call sites (CER-057)."""
from __future__ import annotations

from pathlib import Path

import pytest

from transpiler.transpiler import TranspileError, transpile


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _transpile(path: Path) -> str:
    return transpile(path.read_text(encoding="utf-8"), source_path=path)


def test_unknown_field_type_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "main.pys",
        "class Character{\n"
        "    private string name\n"
        "    private Heritage heritage\n"
        "}\n",
    )
    with pytest.raises(TranspileError, match="Unknown type 'Heritage'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix == "create-class"


def test_unknown_ctor_param_type_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "main.pys",
        "class Character{\n"
        "    constructor(string name, Heritage heritage){\n"
        "        print(name)\n"
        "    }\n"
        "}\n",
    )
    with pytest.raises(TranspileError, match="Unknown type 'Heritage'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix == "create-class"


def test_unknown_return_type_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "main.pys",
        "function Heritage make(){\n"
        "    return null\n"
        "}\n",
    )
    with pytest.raises(TranspileError, match="Unknown type 'Heritage'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix == "create-class"


def test_unknown_nested_typed_decl_is_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "main.pys",
        "function void go(){\n"
        "    Heritage h = null\n"
        "}\n",
    )
    with pytest.raises(TranspileError, match="Unknown type 'Heritage'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix == "create-class"


def test_unknown_generic_arg_is_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, "list.pys", "list<Heritage> xs = []\n")
    with pytest.raises(TranspileError, match="Unknown type 'Heritage'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix == "create-class"

    path2 = _write(tmp_path, "nullable.pys", "nullable<Heritage> h = null\n")
    with pytest.raises(TranspileError, match="Unknown type 'Heritage'") as caught2:
        _transpile(path2)
    assert caught2.value.code == "pys.unknown-type"
    assert caught2.value.suggested_fix == "create-class"


def test_unknown_type_name_ctor_call_is_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, "main.pys", 'Heritage("Miner")\n')
    with pytest.raises(TranspileError, match="Unknown type 'Heritage'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix == "create-class"


def test_unknown_type_top_level_assign_still_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, "main.pys", "Heritage h = null\n")
    with pytest.raises(TranspileError, match="Unknown type 'Heritage'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix == "create-class"


def test_character_heritage_user_scenario_fails_closed(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "main.pys",
        "class Character{\n"
        "    private string name\n"
        "    private Heritage heritage\n"
        "\n"
        "    constructor(string name, Heritage heritage){\n"
        "        this.name = name\n"
        "        this.heritage = heritage\n"
        "    }\n"
        "\n"
        "    public override string toString(){\n"
        '        return "name={this.name} heritage={this.heritage}"\n'
        "    }\n"
        "}\n"
        "\n"
        'Character c = Character("Nori", Heritage("Miner"))\n',
    )
    with pytest.raises(TranspileError, match="Unknown type 'Heritage'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix == "create-class"


def test_unknown_inherits_parent_does_not_offer_create_class(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "main.pys",
        "class Child inherits MissingParent {\n"
        "    public constructor() {}\n"
        "}\n",
    )
    with pytest.raises(TranspileError, match="Unknown type 'MissingParent'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix is None


def test_unknown_cast_type_does_not_offer_create_class(tmp_path: Path) -> None:
    path = _write(tmp_path, "main.pys", "object x = null\nprint((MissingT) x)\n")
    with pytest.raises(TranspileError, match="Unknown type 'MissingT'") as caught:
        _transpile(path)
    assert caught.value.code == "pys.unknown-type"
    assert caught.value.suggested_fix is None


def test_known_local_type_field_and_ctor_allowed(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "main.pys",
        "class Heritage{\n"
        "    private string kind\n"
        "    constructor(string kind){\n"
        "        this.kind = kind\n"
        "    }\n"
        "    public override string toString(){\n"
        '        return this.kind\n'
        "    }\n"
        "}\n"
        "class Character{\n"
        "    private string name\n"
        "    private Heritage heritage\n"
        "    constructor(string name, Heritage heritage){\n"
        "        this.name = name\n"
        "        this.heritage = heritage\n"
        "    }\n"
        "}\n"
        'Character c = Character("Nori", Heritage("Miner"))\n'
        "print(c)\n",
    )
    out = _transpile(path)
    assert "class Character" in out or "Character" in out


def test_lowercase_unknown_callee_still_allowed(tmp_path: Path) -> None:
    """camelCase / lowercase callees stay library-open (not type-name calls)."""
    path = _write(tmp_path, "main.pys", "print(1)\n")
    _transpile(path)


def test_soft_open_unknown_type_with_imports_no_introspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CER-001 §7: with imports and introspection off, do not hard-error inventing types."""
    site = tmp_path / "site"
    (site / "demo").mkdir(parents=True)
    (site / "demo" / "__init__.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr("transpiler.imports.ImportResolver._deps_paths", lambda self: [site])
    path = _write(
        tmp_path,
        "main.pys",
        "import demo\n"
        "class Character{\n"
        "    private MaybeFromLib heritage\n"
        "}\n",
    )
    # Soft-true: unknown library-ish types are unverified, not hard errors.
    transpile(
        path.read_text(encoding="utf-8"),
        source_path=path,
        allow_runtime_introspection=False,
    )
