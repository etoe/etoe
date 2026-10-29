from __future__ import annotations

import os
from pathlib import Path
import tomllib

from etoe import HyperatomTranslator
from etoe.incremental import is_cache_current, manifest_path, snapshot_dependencies, write_manifest


def _write_element(root: Path, notation: str) -> Path:
    folder = root / "C"
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / "C.etoe"
    source.write_text(notation + "\n", encoding="utf-8")
    return source


def test_dependency_snapshot_hash_detects_content_change_even_if_mtime_is_restored(tmp_path):
    source = tmp_path / "source.etoe"
    source.write_text("C-12-(8'4);\n", encoding="utf-8")
    before_stat = source.stat()
    first = snapshot_dependencies([(source, "ether-source")])

    source.write_text("C-13-(8'5);\n", encoding="utf-8")
    os.utime(source, ns=(before_stat.st_atime_ns, before_stat.st_mtime_ns))
    second = snapshot_dependencies([(source, "ether-source")])

    assert first[0]["mtime_ns"] == second[0]["mtime_ns"]
    assert first[0]["sha256"] != second[0]["sha256"]


def test_manifest_writer_and_cache_validation_track_output_and_dependencies(tmp_path):
    source = tmp_path / "C.etoe"
    source.write_text("C-12-(8'4);\n", encoding="utf-8")
    output = tmp_path / "C.png"
    output.write_bytes(b"image-1")
    dependencies = [(source, "ether-source")]
    context = {"writer": "test", "layout": "dot", "format": "png"}

    companion = write_manifest(output, context=context, dependencies=dependencies)
    assert companion == manifest_path(output)
    assert companion is not None
    manifest = tomllib.loads(companion.read_text(encoding="utf-8"))
    assert manifest["schema"] == "etoe.generated-image-manifest.v1"
    assert manifest["dependencies"][0]["path"] == str(source.resolve())
    assert manifest["dependencies"][0]["modified_utc"]
    assert is_cache_current(output, context=context, dependencies=dependencies)

    output.write_bytes(b"manually-modified-image")
    assert not is_cache_current(output, context=context, dependencies=dependencies)


def test_tree_writer_creates_sidecar_skips_unchanged_render_and_invalidates_changed_source(
    tmp_path, monkeypatch,
):
    import etoe.hyperatom_graphviz as graphviz

    source_root = tmp_path / "data" / "atom" / "element"
    source_file = _write_element(source_root, "C-12-(8'4);")
    registry = HyperatomTranslator().translate_directory(source_root)
    output = tmp_path / "graphs" / "C-12.png"
    calls: list[str] = []

    def fake_renderer(dot: str, destination: Path, *, layout: str, format: str) -> Path:
        calls.append(dot)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"fake-image-{len(calls)}".encode("utf-8"))
        return destination

    monkeypatch.setattr(graphviz, "_write_dot_or_render_ex", fake_renderer)

    result = graphviz.write_hyperatom_tree(
        registry,
        "C-12-(8'4)",
        output,
        element_root=source_root,
        format="png",
    )
    companion = manifest_path(result)
    assert result == output
    assert result.is_file()
    assert companion.is_file()
    manifest = tomllib.loads(companion.read_text(encoding="utf-8"))
    dependency_paths = {item["path"] for item in manifest["dependencies"]}
    dependency_mtimes = {item["path"]: item["modified_utc"] for item in manifest["dependencies"]}
    assert str(source_file.resolve()) in dependency_paths
    assert any(path.endswith("style/graphviz/stylesheet.toml") for path in dependency_paths)
    assert dependency_mtimes[str(source_file.resolve())]
    assert len(calls) == 1

    # Identical request + identical source files: no second Graphviz invocation.
    graphviz.write_hyperatom_tree(
        registry,
        "C-12-(8'4)",
        output,
        element_root=source_root,
        format="png",
    )
    assert len(calls) == 1

    # Editing an input source invalidates the sidecar and overwrites the image.
    source_file.write_text("# revised source metadata\nC-12-(8'4);\n", encoding="utf-8")
    graphviz.write_hyperatom_tree(
        registry,
        "C-12-(8'4)",
        output,
        element_root=source_root,
        format="png",
    )
    assert len(calls) == 2
    assert output.read_bytes() == b"fake-image-2"
    refreshed = tomllib.loads(companion.read_text(encoding="utf-8"))
    refreshed_source = next(
        item for item in refreshed["dependencies"]
        if item["path"] == str(source_file.resolve())
    )
    assert refreshed_source["sha256"] != next(
        item["sha256"] for item in manifest["dependencies"]
        if item["path"] == str(source_file.resolve())
    )


def test_stylesheet_edit_invalidates_image_and_reloads_compiled_styles(tmp_path, monkeypatch):
    import shutil
    import etoe.hyperatom_graphviz as graphviz

    project_root = Path(__file__).resolve().parents[1]
    style_root = tmp_path / "custom-style"
    shutil.copytree(project_root / "style" / "shared", style_root / "shared")
    shutil.copytree(project_root / "style" / "graphviz", style_root / "graphviz")
    monkeypatch.setenv("ETOE_STYLE_DIR", str(style_root))

    source_root = tmp_path / "data" / "atom" / "element"
    _write_element(source_root, "C-12-(8'4);")
    registry = HyperatomTranslator().translate_directory(source_root)
    output = tmp_path / "graphs" / "C-12.png"
    generated_dot: list[str] = []

    def fake_renderer(dot: str, destination: Path, *, layout: str, format: str) -> Path:
        generated_dot.append(dot)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"style-render-{len(generated_dot)}".encode("utf-8"))
        return destination

    monkeypatch.setattr(graphviz, "_write_dot_or_render_ex", fake_renderer)
    args = dict(element_root=source_root, format="png", mode="Light", target="GraphViz")
    graphviz.write_hyperatom_tree(registry, "C-12-(8'4)", output, **args)
    assert len(generated_dot) == 1
    assert 'bgcolor="#FFFFFF"' in generated_dot[0]

    graphviz.write_hyperatom_tree(registry, "C-12-(8'4)", output, **args)
    assert len(generated_dot) == 1

    stylesheet = style_root / "graphviz" / "stylesheet.toml"
    stylesheet.write_text(
        stylesheet.read_text(encoding="utf-8").replace(
            'bgcolor = "#FFFFFF"', 'bgcolor = "#FAFAFA"', 1,
        ),
        encoding="utf-8",
    )
    graphviz.write_hyperatom_tree(registry, "C-12-(8'4)", output, **args)
    assert len(generated_dot) == 2
    assert 'bgcolor="#FAFAFA"' in generated_dot[1]
