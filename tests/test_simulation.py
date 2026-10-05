from etoe.simulation import STAEWorld, SimulationConfig


def test_etheron_count_is_conserved_during_microstate_steps():
    world = STAEWorld(SimulationConfig(L_AE=8, T_AE=8, tau_move=3, default_delay=0))
    world.add_etheron((0, 0, 0), direction=(1, 0, 0))
    world.add_etheron((0, 0, 0), direction=(-1, 0, 0))
    initial = len(world.etherons)
    world.step(6)
    assert len(world.etherons) == initial


def test_four_state_cycle_can_complete():
    world = STAEWorld(SimulationConfig(L_AE=8, T_AE=8, tau_move=3, default_delay=0))
    i = world.add_etheron((0, 0, 0), direction=(1, 0, 0))
    states = [world.etherons.state[i]]
    world.step(); states.append(world.etherons.state[i])
    world.step(); states.append(world.etherons.state[i])
    world.step(); states.append(world.etherons.state[i])
    assert states[:4] == [1, 3, 4, 1]
