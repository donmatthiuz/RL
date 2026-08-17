import numpy as np

from src import WarehouseEnv, evaluate_greedy, train_q_learning, train_sarsa


def test_state_encoding_and_pickup_delivery():
    env = WarehouseEnv(max_steps=20)
    state, _ = env.reset()
    assert state == 0

    # (0, 0) -> (0, 1) -> R=(1, 1), donde recoge el paquete.
    env.step(1)
    state, _, terminated, _, info = env.step(2)
    assert not terminated
    assert info["carrying"]
    assert state == ((1 * 8 + 1) * 2 + 1)


def test_congestion_and_truncation():
    env = WarehouseEnv(max_steps=1)
    env.reset(options={"start_position": (4, 2), "carrying": True})
    _, reward, terminated, truncated, info = env.step(1)
    assert reward == -11.0
    assert info["congestion"]
    assert not terminated and truncated


def test_algorithms_register_all_required_metrics():
    for train in (train_sarsa, train_q_learning):
        q_table, history = train(WarehouseEnv(max_steps=30), episodes=20, seed=7)
        assert q_table.shape == (128, 4)
        assert all(len(values) == 20 for values in history.__dict__.values())


def test_greedy_evaluation_uses_requested_episode_count():
    env = WarehouseEnv(max_steps=5)
    result = evaluate_greedy(env, np.zeros((128, 4)), episodes=7, seed=9)
    assert len(result.rewards) == 7
    assert len(result.steps) == 7
