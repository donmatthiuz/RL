import numpy as np

from polym4v.agents.base import Action, Policy


class Always:
    """Política mínima para probar el contrato: siempre la misma acción."""

    def __init__(self, action):
        self.name = f"always-{action.name.lower()}"
        self.action = action
        self.resets = 0

    def act(self, obs, info=None):
        return int(self.action)

    def reset(self):
        self.resets += 1


class WithoutReset:
    name = "incompleta"

    def act(self, obs, info=None):
        return 0


def test_actions_match_the_environment_space():
    assert [(a.name, a.value) for a in Action] == [
        ("WAIT", 0),
        ("BUY_YES", 1),
        ("BUY_NO", 2),
        ("SELL", 3),
    ]


def test_a_policy_with_act_and_reset_follows_the_contract():
    policy = Always(Action.BUY_YES)

    assert isinstance(policy, Policy)
    assert Action(policy.act(np.zeros(19, dtype=np.float32))) is Action.BUY_YES
    policy.reset()
    assert policy.resets == 1


def test_a_policy_without_reset_does_not():
    assert not isinstance(WithoutReset(), Policy)
