from etoe.evolution import MatterEvolutionPipeline
from etoe.matter import MatterLevel
from etoe.simulation import STAEWorld, SimulationConfig, approximately_conserved, inertness_invariants
from etoe.visualization import world_snapshot


def test_inertness_invariants_compare_exactly():
    before = inertness_invariants([((1, 0, 0), 2, 4), ((-1, 0, 0), 2, 4)])
    after = inertness_invariants([((1, 0, 0), 2, 4), ((-1, 0, 0), 2, 4)])
    assert approximately_conserved(before, after)


def test_evolution_pipeline_contains_all_stair_transitions():
    p = MatterEvolutionPipeline()
    assert p.next_transition(MatterLevel.E1).target == MatterLevel.E2
    assert p.next_transition(MatterLevel.E7).target == MatterLevel.E8


def test_visualization_snapshot_is_json_ready_shape():
    world = STAEWorld(SimulationConfig(L_AE=8, T_AE=8))
    world.add_etheron((0, 0, 0))
    snapshot = world_snapshot(world)
    assert snapshot["time"] == 0
    assert snapshot["etherons"][0]["position"] == (0, 0, 0)
