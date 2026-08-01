

import time
import numpy as np
import matplotlib.pyplot as plt



def build_elevator_mdp(n_floors=5, p_demand=0.3,
                        step_cost=-1, serve_reward=10, unnecessary_move_cost=-0.5):
    actions = ['UP', 'DOWN', 'STAY']
    n_actions = len(actions)
    floor_range = range(1, n_floors + 1)

    states = [(p, d) for p in floor_range for d in (0, 1)]
    state_index = {s: i for i, s in enumerate(states)}
    n_states = len(states)

    P = np.zeros((n_states, n_actions, n_states))
    R = np.zeros((n_states, n_actions))

    for s in states:
        p, d = s
        si = state_index[s]
        for ai, a in enumerate(actions):

            # 1. Transicion deterministica del piso
            if a == 'UP':
                new_p = min(p + 1, n_floors)
            elif a == 'DOWN':
                new_p = max(p - 1, 1)
            else:  # STAY
                new_p = p

            moved = a in ('UP', 'DOWN')

            # 2. Se atiende la demanda si te moviste y habia demanda pendiente
            served = moved and (d == 1)

            # 3. Recompensa de este paso
            if served:
                reward = serve_reward
            else:
                reward = step_cost
                if moved and d == 0:
                    reward += unnecessary_move_cost  # movimiento innecesario

            R[si, ai] = reward

            # 4. Transicion de la demanda
            if served:
                # demanda recien atendida: puede aparecer una nueva con p_demand
                P[si, ai, state_index[(new_p, 1)]] += p_demand
                P[si, ai, state_index[(new_p, 0)]] += (1 - p_demand)
            elif d == 1:
                # STAY con demanda pendiente: sigue pendiente con certeza
                P[si, ai, state_index[(new_p, 1)]] += 1.0
            else:
                # d == 0 y no se atendio nada: puede aparecer demanda nueva
                P[si, ai, state_index[(new_p, 1)]] += p_demand
                P[si, ai, state_index[(new_p, 0)]] += (1 - p_demand)

    return P, R, states, actions, state_index



def value_iteration(P, R, gamma=0.95, theta=1e-6, max_iter=10_000):
    n_states, n_actions, _ = P.shape
    V = np.zeros(n_states)

    for it in range(1, max_iter + 1):
        # Q[s, a] = R[s,a] + gamma * sum_s' P[s,a,s'] * V[s']
        Q = R + gamma * np.einsum('san,n->sa', P, V)
        V_new = Q.max(axis=1)

        if np.max(np.abs(V_new - V)) < theta:
            V = V_new
            break
        V = V_new

    Q = R + gamma * np.einsum('san,n->sa', P, V)
    policy = Q.argmax(axis=1)
    return V, policy, it



def policy_evaluation(policy, P, R, gamma=0.95, theta=1e-6, max_iter=10_000):

    n_states = P.shape[0]
    V = np.zeros(n_states)
    bellman_applications = 0

    for _ in range(max_iter):
        delta = 0.0
        for s in range(n_states):
            a = policy[s]
            v_new = R[s, a] + gamma * P[s, a] @ V
            bellman_applications += 1
            delta = max(delta, abs(v_new - V[s]))
            V[s] = v_new
        if delta < theta:
            break
    return V, bellman_applications


def policy_iteration(P, R, gamma=0.95, theta=1e-6):
    n_states, n_actions, _ = P.shape
    policy = np.zeros(n_states, dtype=int)  # política inicial a lo random

    n_iterations_ext = 0
    total_bellman_applications = 0

    while True:
        n_iterations_ext += 1

        # Evaluar poltica actual
        V, eval_applications = policy_evaluation(policy, P, R, gamma, theta)
        total_bellman_applications += eval_applications

        # Aplica el operador bellman
        policy_stable = True
        new_policy = policy.copy()
        for s in range(n_states):
            Q_s = R[s] + gamma * (P[s] @ V)
            total_bellman_applications += 1  # un backup por estado evaluado
            best_a = np.argmax(Q_s)
            if best_a != policy[s]:
                policy_stable = False
            new_policy[s] = best_a

        policy = new_policy
        if policy_stable:
            break

    return V, policy, n_iterations_ext, total_bellman_applications


def print_results(nombre, states, state_index, actions, V, policy, n_iters, elapsed, extra_info=None):
    print(f"\n{nombre}")
    print(f"Iteraciones hasta convergencia : {n_iters}")
    if extra_info:
        for k, v in extra_info.items():
            print(f"{k:<32}: {v}")
    print(f"Tiempo de ejecucion (segundos)  : {elapsed:.6f}")

    col_labels = ["Estado (p,d)", "V*(s)", "pi*(s)"]
    cell_text = [[str(s), f"{V[state_index[s]]:.4f}", actions[policy[state_index[s]]]] for s in states]

    fig_height = 0.5 + 0.35 * len(states)
    fig, ax = plt.subplots(figsize=(5, fig_height))
    ax.axis("off")
    ax.set_title(nombre, fontsize=14, fontweight="bold", pad=12)

    table = ax.table(cellText=cell_text, colLabels=col_labels, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor("#F2F2F2" if row % 2 == 0 else "white")

    fig.tight_layout()
    filename = f"{nombre.lower().replace(' ', '_')}.png"
    fig.savefig(filename, dpi=150)
    print(f"Tabla guardada en: {filename}")

    try:
        from IPython.display import Image, display
        display(Image(filename=filename))
    except ImportError:
        pass
    plt.close(fig)



if __name__ == "__main__":
    P, R, states, actions, state_index = build_elevator_mdp(
        n_floors=5, p_demand=0.3
    )

    print(f"Numero de estados: {len(states)}")
    print(f"Acciones: {actions}")

    # --- Value Iteration ---
    t0 = time.perf_counter()
    V_vi, policy_vi, iters_vi = value_iteration(P, R, gamma=0.95, theta=1e-6)
    t1 = time.perf_counter()
    tiempo_vi = t1 - t0

    print_results(
        "VALUE ITERATION", states, state_index, actions, V_vi, policy_vi,
        n_iters=iters_vi, elapsed=tiempo_vi
    )

    # Policy Iteration
    t0 = time.perf_counter()
    V_pi, policy_pi, iters_pi_ext, bellman_apps_pi = policy_iteration(
        P, R, gamma=0.95, theta=1e-6
    )
    t1 = time.perf_counter()
    tiempo_pi = t1 - t0

    print_results(
        "POLICY ITERATION", states, state_index, actions, V_pi, policy_pi,
        n_iters=iters_pi_ext, elapsed=tiempo_pi,
        extra_info={"Aplicaciones totales del operador de Bellman": bellman_apps_pi}
    )

    # --- Comparacion final ---
    print(f"\n{'='*55}")
    print("  COMPARACION")
    print(f"{'='*55}")
    print("Coinciden las politicas VI y PI:",
          np.array_equal(policy_vi, policy_pi))
    print("Diferencia maxima entre V(VI) y V(PI):",
          np.max(np.abs(V_vi - V_pi)))
    print(f"Tiempo VI: {tiempo_vi:.6f} s   |   Tiempo PI: {tiempo_pi:.6f} s")
