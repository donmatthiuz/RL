DEMAND_MAP = {"bajo": 5, "medio": 15, "alto": 25, "critico": 40}
DEMAND_ORDER = ["bajo", "medio", "alto", "critico"]
INVENTORY_MAX = 100.0
DEMAND_MAX = 40.0
EXPIRY_MAX = 60.0
EXPIRY_THRESHOLD = 7
SUPPLY_CAP = 20.0

FEATURE_NAMES = [
    "bias",
    "inv_n",
    "inv_n2",
    "exp_n",
    "near_expiry",
    "dem_medio",
    "dem_alto",
    "dem_critico",
    "dias_cobertura",
    "riesgo_merma",
    "inv_x_near_expiry",
    "brecha_stockout",
]
N_FEATURES = len(FEATURE_NAMES)


def _normalizar_demanda(demand_level):
    if isinstance(demand_level, str):
        return demand_level.replace("í", "i")
    return demand_level


def preprocess_state(state):
    inventory, days_to_expiry, demand_level = state
    demand_level = _normalizar_demanda(demand_level)
    daily_demand = DEMAND_MAP[demand_level]

    inv = float(min(max(inventory, 0.0), INVENTORY_MAX))
    days = float(min(max(days_to_expiry, 1.0), EXPIRY_MAX))

    inv_n = inv / INVENTORY_MAX
    exp_n = (days - 1.0) / (EXPIRY_MAX - 1.0)
    near_expiry = 1.0 if days <= EXPIRY_THRESHOLD else 0.0
    dias_cobertura = min(inv / daily_demand, SUPPLY_CAP) / SUPPLY_CAP
    riesgo_merma = max(0.0, inv - daily_demand * days) / INVENTORY_MAX

    features = [0.0] * N_FEATURES
    features[0] = 1.0
    features[1] = inv_n
    features[2] = inv_n * inv_n
    features[3] = exp_n
    features[4] = near_expiry
    features[5] = 1.0 if demand_level == "medio" else 0.0
    features[6] = 1.0 if demand_level == "alto" else 0.0
    features[7] = 1.0 if demand_level == "critico" else 0.0
    features[8] = dias_cobertura
    features[9] = riesgo_merma
    features[10] = inv_n * near_expiry
    features[11] = max(0.0, daily_demand - inv) / DEMAND_MAX
    return features


def preprocess_state_original(state):
    inventory, days_to_expiry, demand_level = state
    demand_level = _normalizar_demanda(demand_level)
    demand_idx = {"bajo": 0, "medio": 1, "alto": 2, "critico": 3}[demand_level]
    return [float(inventory), float(days_to_expiry), float(demand_idx)]


class LinearApproximator:
    def __init__(self, n_features=N_FEATURES, n_actions=6, q_init=0.0,
                 normalize_step=True):
        self.n_features = n_features
        self.n_actions = n_actions
        self.normalize_step = normalize_step
        self.weights = [[0.0] * n_features for _ in range(n_actions)]
        if q_init != 0.0:
            for a in range(n_actions):
                self.weights[a][0] = q_init

    def predict(self, features, action):
        w = self.weights[action]
        return sum(w[i] * features[i] for i in range(self.n_features))

    def update(self, features, action, target, alpha=0.05):
        error = target - self.predict(features, action)
        if self.normalize_step:
            norm2 = sum(f * f for f in features)
            step = alpha / norm2 if norm2 > 0.0 else 0.0
        else:
            step = alpha
        w = self.weights[action]
        for i in range(self.n_features):
            w[i] += step * error * features[i]
        return error


def cota_estabilidad(features):
    norm2 = sum(f * f for f in features)
    return float("inf") if norm2 == 0.0 else 2.0 / norm2
