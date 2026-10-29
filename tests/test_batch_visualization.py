"""Batch visualization tests that never invoke Graphviz."""

from pathlib import Path

import pytest

from etoe.batch_visualization import (
    BatchVisualizationJob,
    BatchVisualizationPlan,
    execute_batch_visualizations,
    plan_batch_visualizations,
)
from etoe.hyperatom_translation import HYPERATOM_KIND, HyperatomTranslator


DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "atom" / "element"


@pytest.fixture(scope="module")
def registry():
    return HyperatomTranslator().translate_directory(DATA_ROOT)


def test_batch_plan_covers_source_trees_elements_and_all_selection_kinds(registry):
    plan = plan_batch_visualizations(
        registry,
        element_root=DATA_ROOT,
        all_trees=True,
        all_periodic_maps=True,
        all_hyperatom_maps=True,
        format="dot",
    )
    counts = plan.counts()

    source_hyperatoms = [
        item for item in registry.definitions
        if item.kind == HYPERATOM_KIND and not item.source_path.startswith("<runtime:")
    ]
    assert counts["hyperatom-tree"] == len(source_hyperatoms)
    assert counts["periodic-map"] == len(registry.element_catalog.elements)
    assert counts["hyperatom-map"] > len(registry.element_catalog.elements)
    assert counts["total"] == len(plan.jobs)
    assert all(job.output.suffix == ".dot" for job in plan.jobs)
    assert len({job.output for job in plan.jobs}) == len(plan.jobs)

    tree_jobs = [job for job in plan.jobs if job.kind == "hyperatom-tree"]
    assert any(job.selector == "C-12-(8'4)" for job in tree_jobs)
    assert all(job.hyperatom is not None for job in tree_jobs)

    periodic_jobs = [job for job in plan.jobs if job.kind == "periodic-map"]
    assert any(job.selector == "C" and job.symbols == ("C",) for job in periodic_jobs)

    selection_jobs = [
        job for job in plan.jobs
        if job.kind == "hyperatom-map" and job.selection is not None
    ]
    # This verifies we include the selection catalogs, not only per-element maps.
    assert any(job.selector == "X-40" for job in selection_jobs)
    assert any(job.selector == "transition-metals" for job in selection_jobs)
    assert any(job.selector == "1" for job in selection_jobs)
    assert any(job.selector == "Be_B" for job in selection_jobs)


def test_batch_plan_is_empty_when_no_artifacts_are_selected(registry):
    plan = plan_batch_visualizations(registry, element_root=DATA_ROOT, format="dot")
    assert plan.jobs == ()
    assert plan.counts() == {
        "hyperatom-tree": 0,
        "periodic-map": 0,
        "hyperatom-map": 0,
        "total": 0,
    }


def test_execute_batch_dispatches_to_normal_writers_without_graphviz(monkeypatch, registry, tmp_path):
    """Monkeypatched writers prove dispatch without rendering or writing images."""
    from etoe import hyperatom_graphviz

    atom = next(
        item for item in registry.definitions
        if item.kind == HYPERATOM_KIND and item.canonical == "C-12-(8'4)"
    )
    jobs = (
        BatchVisualizationJob(
            kind="hyperatom-tree", selector=atom.canonical,
            output=tmp_path / "tree.dot", hyperatom=atom,
        ),
        BatchVisualizationJob(
            kind="periodic-map", selector="C", symbols=("C",),
            output=tmp_path / "periodic.dot",
        ),
        BatchVisualizationJob(
            kind="hyperatom-map", selector="X-40", symbols=("K-40-(33'7)", "Ca-40-(32'8)"),
            output=tmp_path / "group-map.dot",
        ),
    )
    plan = BatchVisualizationPlan(jobs)
    calls = []

    def fake_writer(kind):
        def writer(*args, **kwargs):
            output = Path(args[2] if kind == "hyperatom-tree" else args[1])
            calls.append((kind, args, kwargs))
            return output
        return writer

    monkeypatch.setattr(hyperatom_graphviz, "write_hyperatom_tree", fake_writer("hyperatom-tree"))
    monkeypatch.setattr(hyperatom_graphviz, "write_periodic_map", fake_writer("periodic-map"))
    monkeypatch.setattr(hyperatom_graphviz, "write_hyperatom_map", fake_writer("hyperatom-map"))

    outputs = execute_batch_visualizations(
        registry, plan, element_root=DATA_ROOT, format="dot", layout="dot",
    )

    assert outputs == tuple(job.output for job in jobs)
    assert [call[0] for call in calls] == [job.kind for job in jobs]
    assert calls[0][1][1] is atom
    assert calls[1][2]["symbols"] == ("C",)
    assert calls[2][2]["symbols"] == ("K-40-(33'7)", "Ca-40-(32'8)")


def test_cli_batch_requires_an_artifact_selection(capsys):
    from etoe.cli import main

    code = main(["hyperatoms", "batch", "--data-root", str(DATA_ROOT)])
    captured = capsys.readouterr()
    assert code == 2
    assert "choose --all" in captured.err


def test_cli_parser_exposes_batch_modes():
    from etoe.cli import build_parser

    args = build_parser().parse_args([
        "hyperatoms", "batch", "--all-periodic-maps", "--format", "dot",
    ])
    assert args.hyperatoms_command == "batch"
    assert args.all_periodic_maps is True
    assert args.format == "dot"
