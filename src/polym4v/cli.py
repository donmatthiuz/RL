"""Comandos de consulta con salida JSON y errores sin secretos."""

import argparse
import json
import math
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from polymarket import (
    PolymarketError,
    PublicClient,
    RateLimitError,
    RequestRejectedError,
    UserInputError,
)
from pydantic import BaseModel, ValidationError

from .agents.baselines import baselines
from .client import PolymarketClient
from .config import ConfigurationError, PolymarketSettings
from .data.binance import capture_klines, spot_range
from .data.build_dataset import build_dataset
from .data.capture import RawStore, capture_series, write_manifest
from .data.splits import load_exclusions
from .data.trades import capture_trades
from .env.market_data import MarketData
from .env.market_env import PolymarketEnv
from .evaluation.backtest import run_backtest
from .evaluation.metrics import summarize
from .evaluation.verification import TradeVerifier
from .utils.config import (
    DataConfig,
    ExperimentConfig,
    SimulatorConfig,
    load_config,
    load_named,
)
from .utils.paths import get_paths


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Tipo no serializable: {type(value).__name__}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Consulta la API de Polymarket.")
    parser.add_argument("--env-file", default=".env", help="Archivo de configuración")
    commands = parser.add_subparsers(dest="command", required=True)

    markets = commands.add_parser("markets", help="Lista una página de mercados")
    markets.add_argument("--limit", type=int, default=10)
    markets.add_argument("--closed", action="store_true", help="Consulta mercados cerrados")
    markets.add_argument("--cursor", help="next_cursor de la página anterior")

    market = commands.add_parser("market", help="Consulta un mercado por su slug")
    market.add_argument("slug")

    book = commands.add_parser("book", help="Consulta un libro de órdenes")
    book.add_argument("asset_id")

    price = commands.add_parser("price", help="Consulta el precio de compra o venta")
    price.add_argument("asset_id")
    price.add_argument("--side", choices=("BUY", "SELL"), default="BUY")

    midpoint = commands.add_parser("midpoint", help="Consulta el punto medio del precio")
    midpoint.add_argument("asset_id")

    history = commands.add_parser("history", help="Consulta una página de precios históricos")
    history.add_argument("asset_id")
    history.add_argument(
        "--interval", choices=("1h", "6h", "1d", "1w", "1m", "all", "max"), default="1d"
    )
    history.add_argument("--bucket-seconds", type=int, default=3600)
    history.add_argument("--limit", type=int, default=100)
    history.add_argument("--cursor")

    commands.add_parser("account", help="Verifica la conexión autenticada")
    orders = commands.add_parser("open-orders", help="Consulta órdenes de tu cuenta")
    orders.add_argument("--cursor")

    capture = commands.add_parser("capture", help="Archiva el historial crudo de una serie")
    capture.add_argument(
        "--series",
        type=int,
        action="append",
        required=True,
        help="ID de la serie en Gamma; se puede repetir",
    )
    capture.add_argument("--out", default="data/raw", help="Carpeta del crudo")
    capture.add_argument("--limit", type=int, help="Máximo de mercados por serie")
    capture.add_argument("--pause", type=float, default=0.2, help="Segundos entre descargas")

    spot = commands.add_parser("capture-spot", help="Archiva las klines de Binance de una config")
    spot.add_argument("--config", default="configs/data.yaml", help="Config del dataset")
    spot.add_argument("--out", default="data/raw", help="Carpeta del crudo")
    spot.add_argument("--pause", type=float, default=0.1, help="Segundos entre descargas")

    trades = commands.add_parser(
        "capture-trades", help="Archiva los trades taker de los mercados de algunos splits"
    )
    trades.add_argument("--config", default="configs/data.yaml", help="Config del dataset")
    trades.add_argument("--dataset", help="Carpeta del dataset (por defecto, la de la config)")
    trades.add_argument(
        "--split", action="append", help="Split a capturar; se repite (por defecto, val y test)"
    )
    trades.add_argument("--out", default="data/raw", help="Carpeta del crudo")
    trades.add_argument("--pause", type=float, default=0.2, help="Segundos entre mercados")

    build = commands.add_parser(
        "build-dataset", help="Construye markets, prices_raw y spot_1m desde el crudo"
    )
    build.add_argument("--config", default="configs/data.yaml", help="Config del dataset")
    build.add_argument("--raw", help="Carpeta del crudo (por defecto, la de .env)")
    build.add_argument("--out", help="Carpeta de salida (por defecto, processed/<dataset_id>)")

    backtest = commands.add_parser(
        "backtest", help="Corre un baseline sobre un split y guarda sus trayectorias"
    )
    backtest.add_argument("--policy", required=True, help="Nombre del baseline (AGT-03)")
    backtest.add_argument("--split", choices=("train", "val", "test"), default="train")
    backtest.add_argument("--config", default="configs/env.yaml", help="Config del simulador")
    backtest.add_argument("--dataset", help="Carpeta del dataset (por defecto, la de la config)")
    backtest.add_argument("--out", help="Parquet de trayectorias (por defecto, en reports/)")
    backtest.add_argument("--seed", type=int, default=0, help="Semilla de random")
    backtest.add_argument(
        "--params", help="baselines_params.json con los umbrales ajustados en val (tune-baselines)"
    )
    backtest.add_argument(
        "--allow-test", action="store_true", help="Test se evalúa una sola vez (EVA-01)"
    )
    backtest.add_argument(
        "--verify", action="store_true", help="Marca cada ejecución con los trades reales (EVA-11)"
    )
    backtest.add_argument(
        "--strict", action="store_true", help="Solo ejecuta lo que respaldan trades reales"
    )
    backtest.add_argument(
        "--raw", help="Carpeta del crudo con los trades (por defecto, la de .env)"
    )

    evaluate = commands.add_parser(
        "evaluate", help="Evalúa el mejor checkpoint de una corrida en un split"
    )
    evaluate.add_argument("--run", required=True, help="Carpeta de la corrida, en models/<algo>/")
    evaluate.add_argument("--split", choices=("train", "val", "test"), default="val")
    evaluate.add_argument("--dataset", help="Carpeta del dataset (por defecto, la de la config)")
    evaluate.add_argument("--out", help="Parquet de trayectorias (por defecto, en reports/)")
    evaluate.add_argument(
        "--allow-test", action="store_true", help="Test se evalúa una sola vez (EVA-01)"
    )
    evaluate.add_argument("--verify", action="store_true", help="Marca cada ejecución (EVA-11)")
    evaluate.add_argument("--strict", action="store_true", help="Modo estricto (EVA-11)")
    evaluate.add_argument("--raw", help="Carpeta del crudo con los trades")

    tune = commands.add_parser(
        "tune-baselines", help="Ajusta en val los umbrales de los baselines (protocolo, sección 4)"
    )
    tune.add_argument("--config", default="configs/env.yaml", help="Config del simulador")
    tune.add_argument("--dataset", help="Carpeta del dataset (por defecto, la de la config)")
    tune.add_argument("--out", help="Carpeta del reporte (por defecto, reports/val)")

    report = commands.add_parser(
        "report", help="Tabla y figuras de un split con las trayectorias ya calculadas"
    )
    report.add_argument("--split", choices=("train", "val", "test"), default="val")
    report.add_argument("--config", default="configs/env.yaml", help="Config del simulador")
    report.add_argument(
        "--trajectories", help="Carpeta de trayectorias (por defecto, reports/trajectories)"
    )
    report.add_argument("--models", help="Carpeta de modelos (por defecto, la de .env)")
    report.add_argument("--out", help="Carpeta del reporte (por defecto, reports/<split>)")
    report.add_argument(
        "--allow-test", action="store_true", help="Test se evalúa una sola vez (EVA-01)"
    )

    behavior = commands.add_parser(
        "behavior", help="Análisis exploratorio del comportamiento de los agentes (EVA-12)"
    )
    behavior.add_argument("--split", choices=("val", "test"), default="val")
    behavior.add_argument("--config", default="configs/env.yaml", help="Config del simulador")
    behavior.add_argument("--dataset", help="Carpeta del dataset (por defecto, la de la config)")
    behavior.add_argument(
        "--trajectories", help="Carpeta de trayectorias (por defecto, reports/trajectories)"
    )
    behavior.add_argument("--models", help="Carpeta de modelos (por defecto, la de .env)")
    behavior.add_argument("--out", help="Carpeta del reporte (por defecto, reports/<split>)")
    behavior.add_argument(
        "--skip-importance", action="store_true", help="Sin la importancia de features (solo val)"
    )
    behavior.add_argument("--repeats", type=int, default=3, help="Permutaciones por feature")
    behavior.add_argument(
        "--allow-test",
        action="store_true",
        help="Describe las trayectorias de test que ya existen, sin correr políticas",
    )

    ablation = commands.add_parser(
        "ablation", help="Tabla de la ablación de la recompensa con las corridas entrenadas"
    )
    ablation.add_argument("--models", required=True, help="Carpeta con las corridas de la ablación")
    ablation.add_argument("--split", choices=("train", "val"), default="val")
    ablation.add_argument("--out", help="Carpeta del reporte (por defecto, reports/<split>)")

    grid = commands.add_parser(
        "hparams-grid", help="Escribe una config por punto de la búsqueda de AGT-09"
    )
    grid.add_argument("--configs", default="configs", help="Carpeta de las configs base")
    grid.add_argument("--out", default="configs/hparams", help="Carpeta de salida")

    hparams = commands.add_parser(
        "hparams", help="Tabla de la búsqueda de hiperparámetros con las corridas entrenadas"
    )
    hparams.add_argument("--models", required=True, help="Carpeta con una subcarpeta por punto")
    hparams.add_argument("--split", choices=("train", "val"), default="val")
    hparams.add_argument("--out", help="Carpeta del reporte (por defecto, reports)")
    hparams.add_argument("--grid", default="configs/hparams", help="Configs de la búsqueda")
    hparams.add_argument("--final", help="Escribe aquí la mejor config de cada algoritmo (AGT-10)")

    train = commands.add_parser("train", help="Entrena PPO o DQN y elige el mejor checkpoint")
    train.add_argument("--config", default="configs/ppo.yaml", help="Config del experimento")
    train.add_argument(
        "--seed", type=int, action="append", help="Semilla; por defecto, las de la config"
    )
    train.add_argument("--timesteps", type=int, help="Reemplaza total_timesteps (corridas cortas)")
    train.add_argument(
        "--eval-split", choices=("train", "val"), help="Reemplaza eval_split de la config"
    )
    train.add_argument("--dataset", help="Carpeta del dataset (por defecto, la de la config)")
    train.add_argument("--out", help="Carpeta de modelos (por defecto, la de .env)")

    offline = commands.add_parser(
        "collect-offline", help="Recolecta el dataset offline de CQL y BC con los baselines"
    )
    offline.add_argument("--config", default="configs/cql.yaml", help="Config del experimento")
    offline.add_argument("--dataset", help="Carpeta del dataset (por defecto, la de la config)")
    offline.add_argument("--out", help="Carpeta del dataset offline (por defecto, data/offline)")

    config = commands.add_parser("config", help="Valida un YAML y lo muestra resuelto")
    config.add_argument("path", help="Por ejemplo configs/data.yaml")

    manifest = commands.add_parser("manifest", help="Recalcula el hash de cada archivo crudo")
    manifest.add_argument("--out", default="data/raw", help="Carpeta del crudo")
    return parser


def _capture(args: argparse.Namespace) -> Any:
    store = RawStore(args.out)

    def progress(n: int) -> None:
        if n % 250 == 0:
            print(f"{n} mercados procesados", file=sys.stderr, flush=True)

    with PublicClient() as gamma, httpx.Client(timeout=30) as http:
        summaries = [
            capture_series(
                series,
                store,
                gamma=gamma,
                http=http,
                pause=args.pause,
                limit=args.limit,
                on_event=progress,
            )
            for series in args.series
        ]
    manifest = write_manifest(store)
    return {"series": summaries, "files": manifest["n_files"]}


def _capture_spot(args: argparse.Namespace) -> Any:
    config = load_config(args.config, DataConfig)
    store = RawStore(args.out)
    start, end = spot_range(config.date_from, config.date_to)
    with httpx.Client(timeout=30) as http:
        summaries = [
            capture_klines(
                f"{config.asset}USDT", interval, start, end, store, http=http, pause=args.pause
            )
            for interval in ("1m", "1h")
        ]
    manifest = write_manifest(store)
    return {"klines": summaries, "files": manifest["n_files"]}


def _run_policy(policy: Any, label: str, config: Any, args: argparse.Namespace) -> Any:
    """Corre una política en un split con las reglas de `config` y resume sus métricas.

    Lo usan `backtest` (baselines) y `evaluate` (agentes entrenados): todos se evalúan igual.
    """
    if args.split == "test" and not args.allow_test:
        raise ConfigurationError(
            "test se evalúa una sola vez, con todo congelado (EVA-01); usa --allow-test"
        )
    paths = get_paths()
    dataset = Path(args.dataset) if args.dataset else paths.processed / config.dataset_id
    data = MarketData.load(dataset, split=args.split, normalize=config.env.normalize)
    stake = config.env.initial_cash * config.env.stake_fraction
    verifier = None
    if args.verify or args.strict:
        verifier = TradeVerifier.load(
            RawStore(args.raw or paths.raw),
            data.market_ids,
            latency_s=config.env.latency_s,
            tolerance_s=config.env.tolerance_s,
            min_usdc=stake,
        )
    env = PolymarketEnv(data, config.env, config.reward, verifier=verifier, strict=args.strict)
    trajectories = run_backtest(policy, env)
    mode = "_estricto" if args.strict else ""
    name = f"{label}_{args.split}{mode}.parquet"
    out = Path(args.out or paths.reports / "trajectories" / name)
    out.parent.mkdir(parents=True, exist_ok=True)
    trajectories.to_parquet(out, index=False)
    # NaN no es JSON válido: una métrica sin definir (por ejemplo, el Sharpe sin varianza) es null.
    metrics = summarize(trajectories, config.env.initial_cash, stake)
    metrics = {k: None if isinstance(v, float) and math.isnan(v) else v for k, v in metrics.items()}
    return {
        "split": args.split,
        "strict": args.strict,
        "markets_with_trades": None if verifier is None else len(verifier.trades),
        **metrics,
        "trajectories": str(out),
    }


def _backtest(args: argparse.Namespace) -> Any:
    config = load_config(args.config, SimulatorConfig)
    params = json.loads(Path(args.params).read_text(encoding="utf-8")) if args.params else None
    makers = baselines(config.env.costs, seed=args.seed, params=params)
    if args.policy not in makers:
        raise ConfigurationError(f"Baseline desconocido. Disponibles: {', '.join(makers)}.")
    return _run_policy(makers[args.policy](), args.policy, config, args)


def _evaluate(args: argparse.Namespace) -> Any:
    from .agents.adapters import load_policy

    run = Path(args.run)
    config = load_config(run / "config.yaml", ExperimentConfig)
    policy = load_policy(run, config.agent.algo)
    return {"run": run.name, **_run_policy(policy, run.name, config, args)}


def _report(args: argparse.Namespace) -> Any:
    from .evaluation.report import build_report

    if args.split == "test" and not args.allow_test:
        raise ConfigurationError(
            "test se evalúa una sola vez, con todo congelado (EVA-01); usa --allow-test"
        )
    config = load_config(args.config, SimulatorConfig)
    paths = get_paths()
    try:
        return build_report(
            args.split,
            Path(args.trajectories or paths.reports / "trajectories"),
            Path(args.models or paths.models),
            Path(args.out or paths.reports / args.split),
            config.env.initial_cash,
            config.env.initial_cash * config.env.stake_fraction,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc


def _behavior(args: argparse.Namespace) -> Any:
    from .evaluation.behavior import agent_runs, build_behavior, run_importance

    if args.split == "test" and not args.allow_test:
        raise ConfigurationError(
            "test se evaluó una sola vez (EVA-06); usa --allow-test para describir sus trayectorias"
        )
    config = load_config(args.config, SimulatorConfig)
    paths = get_paths()
    dataset = Path(args.dataset) if args.dataset else paths.processed / config.dataset_id
    folder = Path(args.trajectories or paths.reports / "trajectories")
    markets = pd.read_parquet(dataset / "markets.parquet", columns=["market_id", "outcome"])
    outcomes = dict(zip(markets["market_id"], markets["outcome"].astype(int), strict=True))
    importance = steps = None
    if args.split == "val" and not args.skip_importance:
        runs = agent_runs(folder, "val", Path(args.models or paths.models))
        data = MarketData.load(dataset, split="val", normalize=config.env.normalize)
        importance = run_importance(runs, data, repeats=args.repeats)
    if args.split == "test":
        steps = pd.read_parquet(dataset / "steps.parquet", columns=["market_id", "k", "p_yes", "x"])
    try:
        result = build_behavior(
            args.split,
            folder,
            Path(args.out or paths.reports / args.split),
            outcomes,
            config.env,
            importance=importance,
            steps=steps,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc
    if importance is not None:
        result["batch_agreement"] = importance[1]
    return result


def _train(args: argparse.Namespace) -> Any:
    from .agents.offline import offline_path, train_offline
    from .agents.train_sb3 import run_id, train

    config = load_config(args.config, ExperimentConfig)
    if args.timesteps:
        agent = config.agent.model_copy(update={"total_timesteps": args.timesteps})
        config = config.model_copy(update={"agent": agent})
    if args.eval_split:
        config = config.model_copy(update={"eval_split": args.eval_split})
    paths = get_paths()
    dataset = Path(args.dataset) if args.dataset else paths.processed / config.dataset_id
    normalize = config.env.normalize
    train_data = MarketData.load(dataset, split="train", normalize=normalize)
    eval_data = MarketData.load(dataset, split=config.eval_split, normalize=normalize)
    folder = Path(args.out) if args.out else paths.models
    offline_file = None
    if config.offline is not None and config.agent.algo in ("cql", "bc"):
        offline_file = offline_path(paths.offline, config.dataset_id, config.offline, config.reward)
        if not offline_file.exists():
            raise ConfigurationError(
                f"No existe {offline_file}: corre antes collect-offline con esta config"
            )
    runs = []
    for seed in args.seed or config.seeds:
        out = folder / config.agent.algo / run_id(config, seed)
        if offline_file is not None:
            metrics = train_offline(config, seed, offline_file, eval_data, out)
        else:
            metrics = train(config, seed, train_data, eval_data, out)
        runs.append({"run": str(out), "seed": seed, "best": metrics["best"]})
    return {"eval_split": config.eval_split, "runs": runs}


def _collect_offline(args: argparse.Namespace) -> Any:
    from .agents.offline import build_offline_dataset, offline_path

    config = load_config(args.config, ExperimentConfig)
    if config.offline is None:
        raise ConfigurationError("La config no tiene sección offline")
    paths = get_paths()
    dataset = Path(args.dataset) if args.dataset else paths.processed / config.dataset_id
    data = MarketData.load(dataset, split="train", normalize=config.env.normalize)
    folder = Path(args.out) if args.out else paths.offline
    out = offline_path(folder, config.dataset_id, config.offline, config.reward)
    manifest = build_offline_dataset(config, data, out)
    keys = ("transitions", "episodes", "invalid_share", "actions")
    return {"file": str(out), **{key: manifest[key] for key in keys}}


def _capture_trades(args: argparse.Namespace) -> Any:
    config = load_config(args.config, DataConfig)
    dataset = Path(args.dataset) if args.dataset else get_paths().processed / config.dataset_id
    splits = args.split or ["val", "test"]
    markets = pd.read_parquet(dataset / "markets.parquet", columns=["market_id", "w0", "split"])
    markets = markets[markets["split"].isin(splits)].sort_values("w0")
    store = RawStore(args.out)

    def progress(n: int) -> None:
        if n % 250 == 0:
            print(f"{n} de {len(markets)} mercados procesados", file=sys.stderr, flush=True)

    with PublicClient() as client:
        summary = capture_trades(
            zip(markets["market_id"], markets["w0"], strict=True),
            store,
            client=client,
            pause=args.pause,
            on_market=progress,
        )
    manifest = write_manifest(store)
    return {"splits": splits, **summary, "files": manifest["n_files"]}


def _build_dataset(args: argparse.Namespace) -> Any:
    config = load_config(args.config, DataConfig)
    paths = get_paths()
    exclusions = config.test_exclusions
    if not exclusions.is_absolute():
        exclusions = paths.root / exclusions
    raw = RawStore(args.raw or paths.raw)
    out = args.out or paths.processed / config.dataset_id
    manifest = build_dataset(config, raw, load_exclusions(exclusions), out)
    return {key: manifest[key] for key in ("markets_per_split", "discarded_by_reason", "files")}


def _run(args: argparse.Namespace) -> Any:
    if args.command == "capture":
        return _capture(args)
    if args.command == "capture-spot":
        return _capture_spot(args)
    if args.command == "capture-trades":
        return _capture_trades(args)
    if args.command == "build-dataset":
        return _build_dataset(args)
    if args.command == "backtest":
        return _backtest(args)
    if args.command == "train":
        return _train(args)
    if args.command == "evaluate":
        return _evaluate(args)
    if args.command == "report":
        return _report(args)
    if args.command == "behavior":
        return _behavior(args)
    if args.command == "tune-baselines":
        from .evaluation.tuning import tune, write_tuning

        config = load_config(args.config, SimulatorConfig)
        paths = get_paths()
        dataset = Path(args.dataset) if args.dataset else paths.processed / config.dataset_id
        data = MarketData.load(dataset, split="val", normalize=config.env.normalize)
        table, chosen = tune(PolymarketEnv(data, config.env, config.reward))
        out = Path(args.out) if args.out else paths.reports / "val"
        return {"chosen": chosen, "files": write_tuning(table, chosen, out)}
    if args.command == "ablation":
        from .evaluation.ablation import build_ablation

        out = Path(args.out) if args.out else get_paths().reports / args.split
        return build_ablation(Path(args.models), args.split, out)
    if args.command == "hparams-grid":
        from .agents.hparams import write_grid

        written = write_grid(Path(args.configs), Path(args.out))
        return {"configs": len(written), "out": args.out}
    if args.command == "hparams":
        from .evaluation.ablation import build_ablation

        out = Path(args.out) if args.out else get_paths().reports
        title = "Búsqueda de hiperparámetros (AGT-09)"
        result = build_ablation(
            Path(args.models), args.split, out, name="hparams", title=title, by_folder=True
        )
        if args.final:
            from .agents.hparams import write_final

            written = write_final(Path(args.grid), result["best_by_algo"], Path(args.final))
            result["final"] = [str(path) for path in written]
        return result
    if args.command == "collect-offline":
        return _collect_offline(args)
    if args.command == "config":
        return load_named(args.path).model_dump(mode="json")
    if args.command == "manifest":
        manifest = write_manifest(RawStore(args.out))
        return {"files": manifest["n_files"]}
    authenticated = args.command in ("account", "open-orders")
    settings = PolymarketSettings.from_env(args.env_file) if authenticated else None
    with PolymarketClient(settings, authenticated=authenticated) as client:
        match args.command:
            case "markets":
                return client.list_markets(limit=args.limit, closed=args.closed, cursor=args.cursor)
            case "market":
                return client.get_market(slug=args.slug)
            case "book":
                return client.get_order_book(args.asset_id)
            case "price":
                return {
                    "asset_id": args.asset_id,
                    "side": args.side,
                    "price": client.get_price(args.asset_id, side=args.side),
                }
            case "midpoint":
                return {
                    "asset_id": args.asset_id,
                    "midpoint": client.get_midpoint(args.asset_id),
                }
            case "history":
                return client.get_price_history(
                    args.asset_id,
                    interval=args.interval,
                    bucket_seconds=args.bucket_seconds,
                    limit=args.limit,
                    cursor=args.cursor,
                )
            case "account":
                return client.get_account()
            case "open-orders":
                return client.list_open_orders(cursor=args.cursor)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
    except ValidationError as exc:
        print(f"Configuración inválida:\n{exc}", file=sys.stderr)
        return 1
    except ConfigurationError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 1
    except RateLimitError:
        print("Polymarket limitó las peticiones. Espera antes de reintentar.", file=sys.stderr)
        return 1
    except UserInputError:
        print("Parámetros o credenciales inválidos. Revisa docs/polymarket.md.", file=sys.stderr)
        return 1
    except RequestRejectedError as exc:
        print(
            f"Polymarket rechazó la consulta (HTTP {exc.status}). Revisa docs/polymarket.md.",
            file=sys.stderr,
        )
        return 1
    except PolymarketError as exc:
        # Las excepciones del SDK pueden contener detalles de la petición.
        print(
            f"No se pudo consultar Polymarket ({type(exc).__name__}). Revisa docs/polymarket.md.",
            file=sys.stderr,
        )
        return 1
    return 0
