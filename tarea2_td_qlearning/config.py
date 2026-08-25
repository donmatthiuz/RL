from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentConfig:
    max_steps: int = 100
    flow_threshold: float = 0.35
    wait_penalty: float = 2.0
    flow_bonus: float = 0.8
    switch_penalty: float = 0.06
