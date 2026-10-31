from pathlib import Path

import pandas as pd
import pytest

from polym4v.data.splits import SplitExclusions, assign_splits, load_exclusions
from polym4v.utils.config import SplitConfig

REPO = Path(__file__).resolve().parents[1]
W0 = 1_780_000_000
SPLIT = SplitConfig(train=0.70, val=0.15, test=0.15)
NONE = SplitExclusions(descripcion="", slugs=frozenset(), rangos_end_date_utc=())


def markets(n, shuffle=False):
    frame = pd.DataFrame(
        {
            "market_id": [f"m{i:03d}" for i in range(n)],
            "slug": [f"s{i}" for i in range(n)],
            "w0": [W0 + 3600 * i for i in range(n)],
        }
    )
    frame["w1"] = frame["w0"] + 3600
    return frame.sample(frac=1, random_state=0) if shuffle else frame


def by_split(frame):
    return {name: group for name, group in frame.groupby("split")}


def test_proportions_follow_the_config():
    kept, removed = assign_splits(markets(20), SPLIT, NONE)
    assert kept["split"].value_counts().to_dict() == {"train": 14, "val": 3, "test": 3}
    assert removed.empty


def test_splits_are_disjoint_and_in_time_order():
    kept, _ = assign_splits(markets(100, shuffle=True), SPLIT, NONE)
    parts = by_split(kept)

    ids = [set(parts[name]["market_id"]) for name in ("train", "val", "test")]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
    assert parts["train"]["w0"].max() < parts["val"]["w0"].min()
    assert parts["val"]["w0"].max() < parts["test"]["w0"].min()


def test_excluded_slugs_leave_test_only():
    exclusions = NONE.model_copy(update={"slugs": frozenset({"s0", "s19"})})

    kept, removed = assign_splits(markets(20), SPLIT, exclusions)

    assert kept.set_index("slug").loc["s0", "split"] == "train"
    assert "s19" not in set(kept["slug"])
    assert removed.to_dict("records") == [{"market_id": "m019", "motivo": "excluido de test (S11)"}]


def test_excluded_ranges_apply_to_window_end():
    last_w1 = W0 + 3600 * 20
    exclusions = SplitExclusions.model_validate(
        {
            "descripcion": "",
            "slugs": [],
            "rangos_end_date_utc": [
                {
                    "desde": pd.Timestamp(last_w1 - 3600, unit="s", tz="UTC").isoformat(),
                    "hasta": pd.Timestamp(last_w1, unit="s", tz="UTC").isoformat(),
                    "motivo": "prueba",
                }
            ],
        }
    )

    kept, removed = assign_splits(markets(20), SPLIT, exclusions)

    assert list(removed["market_id"]) == ["m018", "m019"]
    assert kept["split"].value_counts()["test"] == 1


def test_repo_exclusions_load():
    exclusions = load_exclusions(REPO / "configs" / "test_exclusions.json")
    assert len(exclusions.slugs) == 299
    assert len(exclusions.rangos_end_date_utc) == 1


def test_unknown_keys_in_exclusions_are_rejected(tmp_path):
    path = tmp_path / "exclusiones.json"
    path.write_text('{"descripcion": "", "slugs": [], "rangos_end_date_utc": [], "otro": 1}')
    with pytest.raises(ValueError):
        load_exclusions(path)
