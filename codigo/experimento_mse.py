import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocesamiento_mejorado import (
    DEMAND_MAP,
    DEMAND_ORDER,
    FEATURE_NAMES,
    cota_estabilidad,
    preprocess_state,
    preprocess_state_original,
)

GAMMA = 0.99
ACTIONS = [0, 10, 20, 30, 40, 50]
INVENTORY_LEVELS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
EXPIRY_LEVELS = [1, 7, 14, 30, 60]


def transition(state, action):
    inventory, days_to_expiry, demand_level = state
    daily_demand = DEMAND_MAP[demand_level]
    new_inventory = min(100, max(0, inventory + action - daily_demand))
    new_days = max(1, days_to_expiry - 1)
    return (new_inventory, new_days, demand_level)


def reward(state, action, next_state):
    new_inventory, new_days, _ = next_state
    return new_inventory * 0.5 + (-10 if new_days <= 7 else 0) + (-2 if action > 0 else 0)


def build_state_space():
    declared = [
        (inv, exp, dem)
        for inv in INVENTORY_LEVELS
        for exp in EXPIRY_LEVELS
        for dem in DEMAND_ORDER
    ]
    seen = set(declared)
    frontier = list(declared)
    while frontier:
        s = frontier.pop()
        for a in ACTIONS:
            ns = transition(s, a)
            if ns not in seen:
                seen.add(ns)
                frontier.append(ns)
    return declared, sorted(seen)


def value_iteration(states, tol=1e-10, max_iter=20000):
    V = {s: 0.0 for s in states}
    for _ in range(max_iter):
        delta = 0.0
        for s in states:
            best = None
            for a in ACTIONS:
                ns = transition(s, a)
                q = reward(s, a, ns) + GAMMA * V[ns]
                if best is None or q > best:
                    best = q
            delta = max(delta, abs(best - V[s]))
            V[s] = best
        if delta < tol:
            break
    Q = {}
    for s in states:
        Q[s] = [reward(s, a, transition(s, a)) + GAMMA * V[transition(s, a)] for a in ACTIONS]
    return V, Q


def solve_ridge(X, y, lam=1e-8):
    n = len(X[0])
    A = [[0.0] * (n + 1) for _ in range(n)]
    for i in range(n):
        for j in range(n):
            A[i][j] = sum(row[i] * row[j] for row in X)
        A[i][i] += lam
        A[i][n] = sum(X[k][i] * y[k] for k in range(len(X)))
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(A[r][col]))
        if abs(A[piv][col]) < 1e-14:
            continue
        A[col], A[piv] = A[piv], A[col]
        p = A[col][col]
        for j in range(col, n + 1):
            A[col][j] /= p
        for r in range(n):
            if r != col and A[r][col] != 0.0:
                f = A[r][col]
                for j in range(col, n + 1):
                    A[r][j] -= f * A[col][j]
    return [A[i][n] for i in range(n)]


def fit_and_eval(phi, train_states, test_states, Q):
    n_actions = len(ACTIONS)
    weights = []
    for a in range(n_actions):
        X = [phi(s) for s in train_states]
        y = [Q[s][a] for s in train_states]
        weights.append(solve_ridge(X, y))

    def mse(states):
        total = 0.0
        for s in states:
            f = phi(s)
            for a in range(n_actions):
                pred = sum(weights[a][i] * f[i] for i in range(len(f)))
                total += (Q[s][a] - pred) ** 2
        return total / (len(states) * n_actions)

    return weights, mse(train_states), mse(test_states)


def per_state_errors(phi, weights, states, Q):
    rows = []
    for s in states:
        f = phi(s)
        err = 0.0
        for a in range(len(ACTIONS)):
            pred = sum(weights[a][i] * f[i] for i in range(len(f)))
            err += (Q[s][a] - pred) ** 2
        rows.append(err / len(ACTIONS))
    return rows


def preprocess_state_bias(state):
    return [1.0] + preprocess_state_original(state)


def preprocess_state_solo_normalizado(state):
    inventory, days_to_expiry, demand_level = state
    demand_level = demand_level.replace("í", "i")
    demand_idx = {"bajo": 0, "medio": 1, "alto": 2, "critico": 3}[demand_level]
    return [1.0, inventory / 100.0, (days_to_expiry - 1.0) / 59.0, demand_idx / 3.0]


def jacobi_eigenvalues(M, sweeps=100, tol=1e-12):
    n = len(M)
    A = [row[:] for row in M]
    for _ in range(sweeps):
        off = sum(A[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-18:
                    continue
                theta = (A[q][q] - A[p][p]) / (2.0 * A[p][q])
                t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + (theta * theta + 1.0) ** 0.5)
                c = 1.0 / (t * t + 1.0) ** 0.5
                s = t * c
                for k in range(n):
                    akp, akq = A[k][p], A[k][q]
                    A[k][p] = c * akp - s * akq
                    A[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = A[p][k], A[q][k]
                    A[p][k] = c * apk - s * aqk
                    A[q][k] = s * apk + c * aqk
    return sorted(A[i][i] for i in range(n))


def numero_condicion(phi, states):
    X = [phi(s) for s in states]
    n = len(X[0])
    N = float(len(X))
    G = [[sum(r[i] * r[j] for r in X) / N for j in range(n)] for i in range(n)]
    ev = jacobi_eigenvalues(G)
    lo = max(ev[0], 1e-18)
    return {"lambda_min": ev[0], "lambda_max": ev[-1], "kappa": ev[-1] / lo}


def aporte_por_componente(phi, states, names):
    n = len(names)
    sums = [0.0] * n
    for s in states:
        f = phi(s)
        for i in range(n):
            sums[i] += f[i] * f[i]
    total = sum(sums)
    return {names[i]: 100.0 * sums[i] / total for i in range(n)}


def sgd_stability_probe(phi, states, Q, alpha, n_passes=5):
    dim = len(phi(states[0]))
    w = [0.0] * dim
    for _ in range(n_passes):
        for s in states:
            f = phi(s)
            pred = sum(w[i] * f[i] for i in range(dim))
            error = Q[s][0] - pred
            for i in range(dim):
                w[i] += alpha * error * f[i]
            if any(abs(x) > 1e12 or x != x for x in w):
                return None
    return max(abs(x) for x in w)


def main():
    declared, reachable = build_state_space()
    V, Q = value_iteration(reachable)

    test_states = []
    step = len(declared) / 24.0
    for k in range(24):
        test_states.append(declared[int(k * step)])
    test_states = sorted(set(test_states))
    train_states = [s for s in reachable if s not in set(test_states)]

    w_orig, tr_o, te_o = fit_and_eval(preprocess_state_original, train_states, test_states, Q)
    w_bias, tr_b, te_b = fit_and_eval(preprocess_state_bias, train_states, test_states, Q)
    w_new, tr_n, te_n = fit_and_eval(preprocess_state, train_states, test_states, Q)

    err_o = per_state_errors(preprocess_state_original, w_orig, test_states, Q)
    err_n = per_state_errors(preprocess_state, w_new, test_states, Q)

    norms_o = [sum(f * f for f in preprocess_state_original(s)) for s in declared]
    norms_n = [sum(f * f for f in preprocess_state(s)) for s in declared]

    probe = {}
    for alpha in [0.01, 1e-3, 1e-4, 1.4e-4]:
        probe[str(alpha)] = sgd_stability_probe(preprocess_state_original, train_states, Q, alpha)
    probe_new = {}
    for alpha in [0.01, 0.05, 0.1]:
        probe_new[str(alpha)] = sgd_stability_probe(preprocess_state, train_states, Q, alpha)

    q_vals = [Q[s][a] for s in reachable for a in range(len(ACTIONS))]
    var_q = sum((q - sum(q_vals) / len(q_vals)) ** 2 for q in q_vals) / len(q_vals)

    out = {
        "n_estados_declarados": len(declared),
        "n_estados_alcanzables": len(reachable),
        "n_train": len(train_states),
        "n_test": len(test_states),
        "mse": {
            "original": {"train": tr_o, "test": te_o},
            "original_mas_bias": {"train": tr_b, "test": te_b},
            "mejorado": {"train": tr_n, "test": te_n},
        },
        "reduccion_mse_test_pct": 100.0 * (1 - te_n / te_o),
        "reduccion_vs_bias_pct": 100.0 * (1 - te_n / te_b),
        "r2_test": {
            "original": 1 - te_o / var_q,
            "original_mas_bias": 1 - te_b / var_q,
            "mejorado": 1 - te_n / var_q,
        },
        "numero_condicion": {
            "original": numero_condicion(preprocess_state_original, declared),
            "original_normalizado": numero_condicion(preprocess_state_solo_normalizado, declared),
            "mejorado": numero_condicion(preprocess_state, declared),
        },
        "aporte_norma_pct": {
            "original": aporte_por_componente(
                preprocess_state_original, declared,
                ["inventory", "days_to_expiry", "demand_idx"]),
            "mejorado": aporte_por_componente(preprocess_state, declared, FEATURE_NAMES),
        },
        "varianza_Q": var_q,
        "norma_cuadrada_phi": {
            "original": {"min": min(norms_o), "max": max(norms_o),
                         "alpha_max": 2.0 / max(norms_o)},
            "mejorado": {"min": min(norms_n), "max": max(norms_n),
                         "alpha_max": 2.0 / max(norms_n)},
        },
        "sgd_original": probe,
        "sgd_mejorado": probe_new,
        "tabla_test": [
            {
                "estado": [s[0], s[1], s[2]],
                "q_max": max(Q[s]),
                "accion_optima": ACTIONS[max(range(len(ACTIONS)), key=lambda a: Q[s][a])],
                "mse_original": err_o[i],
                "mse_mejorado": err_n[i],
            }
            for i, s in enumerate(test_states)
        ],
        "pesos_mejorado_a0": dict(zip(FEATURE_NAMES, w_new[0])),
    }

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "resultados", "resultados_44.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
