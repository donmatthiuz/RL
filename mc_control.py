from __future__ import annotations

import argparse
import pickle
import random
from collections import defaultdict
from typing import Dict, List, Tuple

State = Tuple[int, int, int, int]
Action = int

ACTIONS: Tuple[Action, ...] = (0, 1, 2, 3)
ACTION_NAMES = {0: "arriba", 1: "abajo", 2: "izquierda", 3: "derecha"}
ACTION_DELTAS = {0: (-1, 0), 1: (1, 0), 2: (0, -1), 3: (0, 1)}

GRID_SIZE = 6
START_CELL = (0, 0)
T1_CELL = (1, 4)
T2_CELL = (2, 1)
TRAP_CELL = (3, 3)
GOAL_CELL = (5, 5)

STEP_REWARD = -1.0
T1_REWARD = 5.0
T2_REWARD = 3.0
TRAP_REWARD = -10.0
GOAL_REWARD = 20.0

GAMMA = 0.95
EPSILON = 0.10
MAX_STEPS = 200


class GridWorld:
    def __init__(self, gamma: float = GAMMA, max_steps: int = MAX_STEPS):
        self.n = GRID_SIZE
        self.gamma = gamma
        self.max_steps = max_steps

    def start_state(self) -> State:
        return (START_CELL[0], START_CELL[1], 0, 0)

    def is_terminal(self, s: State) -> bool:
        f, c, _, _ = s
        return (f, c) == GOAL_CELL

    def step(self, s: State, a: Action) -> Tuple[State, float]:
        f, c, b1, b2 = s
        df, dc = ACTION_DELTAS[a]
        nf, nc = f + df, c + dc

        if not (0 <= nf < self.n and 0 <= nc < self.n):
            nf, nc = f, c

        reward = STEP_REWARD
        nb1, nb2 = b1, b2

        if (nf, nc) == T1_CELL and b1 == 0:
            reward += T1_REWARD
            nb1 = 1
        if (nf, nc) == T2_CELL and b2 == 0:
            reward += T2_REWARD
            nb2 = 1
        if (nf, nc) == TRAP_CELL:
            reward += TRAP_REWARD
        if (nf, nc) == GOAL_CELL:
            reward += GOAL_REWARD

        return (nf, nc, nb1, nb2), reward

    def all_states(self) -> List[State]:
        return [
            (f, c, b1, b2)
            for f in range(self.n)
            for c in range(self.n)
            for b1 in (0, 1)
            for b2 in (0, 1)
        ]


def make_Q() -> Dict[State, List[float]]:
    return defaultdict(lambda: [0.0] * len(ACTIONS))


def epsilon_greedy_action(Q: Dict[State, List[float]], s: State, epsilon: float,
                           rng: random.Random) -> Action:
    if rng.random() < epsilon:
        return rng.choice(ACTIONS)
    q_s = Q[s]
    max_q = max(q_s)
    best = [a for a, q in enumerate(q_s) if q == max_q]
    return rng.choice(best)


def generate_episode(env: GridWorld, Q: Dict[State, List[float]], epsilon: float,
                      rng: random.Random) -> List[Tuple[State, Action, float]]:
    episode = []
    s = env.start_state()
    for _ in range(env.max_steps):
        if env.is_terminal(s):
            break
        a = epsilon_greedy_action(Q, s, epsilon, rng)
        s_next, r = env.step(s, a)
        episode.append((s, a, r))
        s = s_next
    return episode


def mc_control(
    env: GridWorld,
    num_episodes: int,
    epsilon: float = EPSILON,
    first_visit: bool = True,
    seed: int | None = None,
    log_every: int = 5000,
    checkpoint_episodes: List[int] | None = None,
) -> Tuple[
    Dict[State, List[float]],
    Dict[State, List[int]],
    List[Tuple[int, float]],
    Dict[int, Dict[State, List[float]]],
]:
    rng = random.Random(seed)
    Q = make_Q()
    N: Dict[State, List[int]] = defaultdict(lambda: [0] * len(ACTIONS))
    history: List[Tuple[int, float]] = []
    s0 = env.start_state()

    checkpoint_set = set(checkpoint_episodes or [])
    checkpoints: Dict[int, Dict[State, List[float]]] = {}

    variant = "Primera-Visita" if first_visit else "Cada-Visita"

    for ep in range(1, num_episodes + 1):
        episode = generate_episode(env, Q, epsilon, rng)

        G = 0.0
        visited_first: set[Tuple[State, Action]] = set()

        for t in range(len(episode) - 1, -1, -1):
            s, a, r = episode[t]
            G = env.gamma * G + r

            if first_visit:
                if (s, a) in visited_first:
                    continue
                visited_first.add((s, a))

            N[s][a] += 1
            Q[s][a] += (G - Q[s][a]) / N[s][a]

        if ep in checkpoint_set:
            checkpoints[ep] = {s: list(q) for s, q in Q.items()}

        if log_every and ep % log_every == 0:
            v_s0 = max(Q[s0]) if s0 in Q else 0.0
            history.append((ep, v_s0))
            print(f"[MC {variant}] episodio {ep:>7} | "
                  f"V(s0) ~ {v_s0:7.3f} | estados visitados: {len(Q)}/144")

    return Q, N, history, checkpoints


def greedy_policy(Q: Dict[State, List[float]]) -> Dict[State, Action]:
    return {s: max(range(len(ACTIONS)), key=lambda a: q[a]) for s, q in Q.items()}


def rollout_greedy(env: GridWorld, Q: Dict[State, List[float]],
                    max_steps: int = MAX_STEPS) -> Tuple[List[State], float]:
    s = env.start_state()
    path = [s]
    total_return = 0.0
    discount = 1.0
    for _ in range(max_steps):
        if env.is_terminal(s):
            break
        a = max(range(len(ACTIONS)), key=lambda a: Q[s][a])
        s, r = env.step(s, a)
        total_return += discount * r
        discount *= env.gamma
        path.append(s)
    return path, total_return


def print_rollout(env: GridWorld, Q: Dict[State, List[float]]) -> None:
    path, ret = rollout_greedy(env, Q)
    names = [f"({f},{c},{b1},{b2})" for f, c, b1, b2 in path]
    print(f"\nRuta codiciosa desde s0 ({len(path) - 1} pasos, retorno G0={ret:.3f}):")
    print(" -> ".join(names))


# ---------------------------------------------------------------------------
# Value Iteration (linea base de Programacion Dinamica, para comparar con MC)
# ---------------------------------------------------------------------------

def value_iteration(
    env: GridWorld,
    theta: float = 1e-8,
    max_iters: int = 10_000,
) -> Tuple[Dict[State, float], Dict[State, Action], int]:
    """Value Iteration exacto sobre el mismo MDP de GridWorld.

    Las transiciones son deterministas, asi que Q(s,a) = r(s,a) + gamma * V(s').
    Devuelve V*, la politica optima (accion por estado, None en estados
    terminales) y el numero de barridos hasta converger.
    """
    states = env.all_states()
    V: Dict[State, float] = {s: 0.0 for s in states}

    for it in range(1, max_iters + 1):
        delta = 0.0
        new_V: Dict[State, float] = {}
        for s in states:
            if env.is_terminal(s):
                new_V[s] = 0.0
                continue
            q_values = [env.step(s, a)[1] + env.gamma * V[env.step(s, a)[0]] for a in ACTIONS]
            new_V[s] = max(q_values)
            delta = max(delta, abs(new_V[s] - V[s]))
        V = new_V
        if delta < theta:
            break

    policy: Dict[State, Action] = {}
    for s in states:
        if env.is_terminal(s):
            continue
        q_values = [env.step(s, a)[1] + env.gamma * V[env.step(s, a)[0]] for a in ACTIONS]
        policy[s] = max(range(len(ACTIONS)), key=lambda a: q_values[a])

    return V, policy, it


# ---------------------------------------------------------------------------
# Visualizacion: V(s) y politica greedy en grilla, para comparar MC vs VI
# ---------------------------------------------------------------------------

ACTION_ARROWS = {0: "↑", 1: "↓", 2: "←", 3: "→"}
LANDMARKS = {START_CELL: "S", T1_CELL: "T1", T2_CELL: "T2", TRAP_CELL: "P", GOAL_CELL: "G"}


def value_and_policy_grid(
    values: Dict[State, object],
    policy: Dict[State, Action] | None = None,
    n: int = GRID_SIZE,
    b1: int = 0,
    b2: int = 0,
):
    """Arma las grillas V(s) y accion greedy para (f, c, b1, b2) fijando b1, b2.

    Acepta dos formas de entrada:
    - `values` = Q de Monte Carlo (estado -> lista de Q(s,a)): se usa
      V(s) = max_a Q(s,a) y la accion greedy = argmax_a Q(s,a). `policy` debe
      quedar en None.
    - `values` = V* de Value Iteration (estado -> float) junto con `policy`
      (estado -> accion optima): se usan directamente.
    """
    import numpy as np

    V = np.zeros((n, n))
    P = np.zeros((n, n), dtype=int)
    for f in range(n):
        for c in range(n):
            s = (f, c, b1, b2)
            if policy is None:
                q = values.get(s, [0.0] * len(ACTIONS))
                V[f, c] = max(q)
                P[f, c] = int(max(range(len(ACTIONS)), key=lambda a: q[a]))
            else:
                V[f, c] = values.get(s, 0.0)
                P[f, c] = policy.get(s, 0)
    return V, P


def _draw_value_policy(ax, V, policy, title: str, b1: int, b2: int, vmin=None, vmax=None):
    im = ax.imshow(V, cmap="viridis", vmin=vmin, vmax=vmax)
    for f in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if (f, c) == GOAL_CELL:
                label = "G"
            else:
                label = ACTION_ARROWS[policy[f, c]]
                if (f, c) in LANDMARKS:
                    label = f"{LANDMARKS[(f, c)]}\n{label}"
            ax.text(c, f, label, ha="center", va="center",
                     color="white", fontsize=11, fontweight="bold")
    ax.set_title(f"{title}\n(b1={b1}, b2={b2})")
    ax.set_xticks(range(GRID_SIZE))
    ax.set_yticks(range(GRID_SIZE))
    ax.set_xlabel("columna (c)")
    ax.set_ylabel("fila (f)")
    return im


def plot_value_iteration_vs_mc(
    V_vi: Dict[State, float],
    policy_vi: Dict[State, Action],
    Q_mc: Dict[State, List[float]],
    b1: int = 0,
    b2: int = 0,
    title_vi: str = "Value Iteration (optimo)",
    title_mc: str = "Monte Carlo (greedy sobre Q)",
):
    """Grafica lado a lado V(s) y la politica greedy de Value Iteration contra
    la de Monte Carlo, fijando (b1, b2), en la misma escala de color para que
    sean directamente comparables.
    """
    import matplotlib.pyplot as plt

    V1, P1 = value_and_policy_grid(V_vi, policy=policy_vi, b1=b1, b2=b2)
    V2, P2 = value_and_policy_grid(Q_mc, b1=b1, b2=b2)

    vmin = min(V1.min(), V2.min())
    vmax = max(V1.max(), V2.max())

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    im = None
    for ax, V, P, title in zip(axes, (V1, V2), (P1, P2), (title_vi, title_mc)):
        im = _draw_value_policy(ax, V, P, title, b1, b2, vmin=vmin, vmax=vmax)

    fig.colorbar(im, ax=axes, shrink=0.8, label="V(s)")
    plt.show()
    return fig


