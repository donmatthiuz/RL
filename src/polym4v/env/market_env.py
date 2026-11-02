"""`PolymarketEnv`: un episodio es un mercado horario (ENV-04, docs/09 y docs/notas/mdp.md).

- **Observación:** las 13 features de mercado de `steps` en `t`, más el estado del agente
  (`pos_side`, `entry_price` y `upnl`). Todo se conoce en `t` (S1 y S3).
- **Ejecución (S4):** una orden decidida en `t` se ejecuta al primer precio con fecha posterior a
  `t + latency_s`, como mucho a `t + tolerance_s`. Si no hay precio, se cancela.
- **Acciones inválidas (S6):** se ejecutan como `WAIT`; `info` guarda la pedida y la ejecutada.
- **Fin (S10):** no se abren posiciones en los últimos minutos y en `w1` la posición se liquida a
  1 o 0, sin comisión.
- **Validación (EVA-11):** con un `verifier`, cada ejecución se marca como respaldada o no por
  trades reales; en modo estricto, las no respaldadas no se ejecutan (ADR-017).
"""

from collections.abc import Callable
from typing import Any

import gymnasium as gym
import numpy as np

from ..agents.base import Action
from ..utils.config import EnvConfig, RewardConfig
from .execution import Fill, buy, sell
from .market_data import Episode, MarketData
from .portfolio import FLAT, NO, YES, Portfolio, side_price
from .reward import RewardState, reward

AGENT_FEATURES = ("pos_side", "entry_price", "upnl")
# Claves de `info` en cada paso (INF-06). Describen la decisión tomada en `ts` y el estado de la
# cartera en el instante siguiente. En `reset`, las de la acción y la orden valen None.
INFO_KEYS = (
    "market_id",
    "k",
    "ts",
    "p_yes",
    "action",
    "action_executed",
    "action_valid",
    "order_status",
    "exec_ts",
    "exec_p",
    "exec_verified",
    "fill_price",
    "fill_shares",
    "fee",
    "position_side",
    "position_size",
    "cash",
    "portfolio_value",
    "fees_paid",
    "reward_components",
)
ORDER_STATUS = ("ejecutada", "sin_precio", "no_verificable", "invalida", "ninguna")
# (market_id, t, buy=compra en equivalente YES, yes_price=precio YES) -> respaldada, o None.
Verifier = Callable[..., bool | None]


class PolymarketEnv(gym.Env[np.ndarray, np.int64]):
    metadata: dict[str, Any] = {"render_modes": []}

    def __init__(
        self,
        data: MarketData,
        config: EnvConfig,
        reward_config: RewardConfig,
        *,
        verifier: Verifier | None = None,
        strict: bool = False,
    ) -> None:
        if config.tolerance_s > data.step_s:
            raise ValueError("tolerance_s no puede superar el paso de la grilla (docs/09, S4)")
        if strict and verifier is None:
            raise ValueError("el modo estricto necesita un verifier con trades reales (EVA-11)")
        self.data, self.config, self.reward_config = data, config, reward_config
        self.verifier, self.strict = verifier, strict
        self.costs = config.costs
        self.stake = config.initial_cash * config.stake_fraction
        # La comisión se redondea hacia arriba: una compra puede costar una fracción del último
        # decimal más que el monto, y abrir exige ese margen en la caja.
        self.open_cash = self.stake + 10.0**-config.costs.fee_decimals
        self.last_open_k = data.n_steps - config.no_open_last_minutes * 60 // data.step_s
        n_features = data.episodes[0].features.shape[1] + len(AGENT_FEATURES)
        self.observation_space = gym.spaces.Box(-np.inf, np.inf, (n_features,), np.float32)
        self.action_space = gym.spaces.Discrete(len(Action))
        self.episode: Episode = data.episodes[0]
        self.k = 0
        self.portfolio = Portfolio(cash=config.initial_cash)
        self.reward_state = RewardState(v0=config.initial_cash, peak=config.initial_cash)
        self.value = config.initial_cash

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Empieza un mercado: el de `options["market_id"]` o uno al azar del split."""
        super().reset(seed=seed)
        market_id = (options or {}).get("market_id")
        if market_id is not None:
            self.episode = self.data[market_id]
        else:
            self.episode = self.data.episodes[int(self.np_random.integers(len(self.data)))]
        cash = self.config.initial_cash
        self.k = 0
        self.portfolio = Portfolio(cash=cash)
        self.reward_state = RewardState(v0=cash, peak=cash)
        self.value = cash
        return self._observation(), self._info(None, None, None, "ninguna", None, None, None, None)

    def step(self, action: Any) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self.k == self.data.n_steps:
            raise RuntimeError("El episodio ya terminó: llama a reset() antes de step()")
        requested = Action(int(action))
        t = int(self.episode.ts[self.k])
        valid = bool(self.action_masks()[requested])
        executed, status = Action.WAIT, "ninguna"
        execution: tuple[int, float] | None = None
        fill: Fill | None = None
        verified: bool | None = None
        if requested != Action.WAIT and not valid:
            status = "invalida"
        elif requested != Action.WAIT:
            execution = self._execution_price(t)
            if execution is None:
                status = "sin_precio"
            else:
                side, fill = self._fill(requested, execution[1])
                verified = self._verify(t, requested, side, fill)
                if self.strict and verified is not True:
                    status, fill = "no_verificable", None
                else:
                    self._apply(requested, side, fill)
                    executed, status = requested, "ejecutada"

        self.k += 1
        done = self.k == self.data.n_steps
        if done:
            self.portfolio.settle(self.episode.outcome)
            value = self.portfolio.cash
        else:
            value = self.portfolio.value(float(self.episode.p_yes[self.k]), self.costs)
        total, components = reward(
            self.reward_config,
            self.reward_state,
            v_prev=self.value,
            v_now=value,
            invalid=requested != Action.WAIT and not valid,
            done=done,
        )
        self.value = value
        info = self._info(
            requested, executed, valid, status, execution, verified, fill, components, t=t
        )
        return self._observation(), total, done, False, info

    def action_masks(self) -> np.ndarray:
        """Acciones válidas en el paso actual (S6), para MaskablePPO y para el backtest."""
        flat = self.portfolio.side == FLAT
        can_open = flat and self.k < self.last_open_k and self.portfolio.cash >= self.open_cash
        return np.array([True, can_open, can_open, not flat])

    def _execution_price(self, t: int) -> tuple[int, float] | None:
        """Primer punto YES con fecha en `(t + latency_s, t + tolerance_s]` (S4)."""
        ep = self.episode
        i = int(np.searchsorted(ep.price_ts, t + self.config.latency_s, side="right"))
        if i < len(ep.price_ts) and ep.price_ts[i] <= t + self.config.tolerance_s:
            return int(ep.price_ts[i]), float(ep.price_p[i])
        return None

    def _fill(self, action: Action, p_yes: float) -> tuple[int, Fill]:
        """Lado operado y operación calculada, sin aplicarla todavía a la cartera."""
        if action == Action.SELL:
            side = self.portfolio.side
            return side, sell(self.portfolio.shares, side_price(p_yes, side), self.costs)
        side = YES if action == Action.BUY_YES else NO
        return side, buy(self.stake, side_price(p_yes, side), self.costs)

    def _apply(self, action: Action, side: int, fill: Fill) -> None:
        if action == Action.SELL:
            self.portfolio.close(fill)
        else:
            self.portfolio.open(side, fill)

    def _verify(self, t: int, action: Action, side: int, fill: Fill) -> bool | None:
        """Comprar YES o vender NO es comprar en equivalente YES; lo demás es vender."""
        if self.verifier is None:
            return None
        buying = action != Action.SELL
        yes_price = fill.price if side == YES else 1.0 - fill.price
        return self.verifier(
            self.episode.market_id, t, buy=buying == (side == YES), yes_price=yes_price
        )

    def _observation(self) -> np.ndarray:
        k = min(self.k, self.data.n_steps - 1)
        position = self.portfolio
        upnl = 0.0
        if position.side != FLAT:
            p_yes = float(self.episode.p_yes[k])
            upnl = (position.liquidation_value(p_yes, self.costs) - position.cost) / self.stake
        agent = np.array([position.side, position.entry_price, upnl], dtype=np.float32)
        return np.concatenate([self.episode.features[k], agent])

    def _info(
        self,
        requested: Action | None,
        executed: Action | None,
        valid: bool | None,
        status: str,
        execution: tuple[int, float] | None,
        verified: bool | None,
        fill: Fill | None,
        components: dict[str, float] | None,
        *,
        t: int | None = None,
    ) -> dict[str, Any]:
        k = self.k - 1 if t is not None else self.k
        return {
            "market_id": self.episode.market_id,
            "k": k,
            "ts": int(self.episode.ts[k]),
            "p_yes": float(self.episode.p_yes[k]),
            "action": None if requested is None else int(requested),
            "action_executed": None if executed is None else int(executed),
            "action_valid": valid,
            "order_status": status,
            "exec_ts": None if execution is None else execution[0],
            "exec_p": None if execution is None else execution[1],
            "exec_verified": verified,
            "fill_price": None if fill is None else fill.price,
            "fill_shares": None if fill is None else fill.shares,
            "fee": 0.0 if fill is None else fill.fee,
            "position_side": self.portfolio.side,
            "position_size": self.portfolio.shares,
            "cash": self.portfolio.cash,
            "portfolio_value": self.value,
            "fees_paid": self.portfolio.fees_paid,
            "reward_components": components,
        }
