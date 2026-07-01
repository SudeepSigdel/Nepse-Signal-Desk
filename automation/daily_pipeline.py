import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

STALE_LOCK_MINUTES = 12 * 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NEPSE scrape + full ML pipeline in sequence.")
    parser.add_argument("--source", choices=["auto", "sharesansar", "merolagani"], default="sharesansar")
    parser.add_argument("--symbols", default="", help="Optional comma-separated symbols.")
    parser.add_argument("--start-date", default="", help="Optional YYYY-MM-DD to pass to the scraper (global start date).")
    parser.add_argument("--delay", type=float, default=0.2, help="Per-symbol delay for scraper.")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping step.")
    parser.add_argument("--skip-parquet", action="store_true", help="Pass --skip-parquet to scraper.")
    parser.add_argument(
        "--model-family",
        choices=["both", "xgboost", "random_forest", "rf"],
        default="both",
        help="Model family to train/evaluate after data prep. 'both' runs XGBoost and Random Forest.",
    )
    return parser.parse_args()


def run_step(label: str, command: list[str], env: dict[str, str], env_overrides: dict[str, str] | None = None) -> None:
    print("\n" + "=" * 78)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] START: {label}")
    print("Command:", " ".join(command))
    if env_overrides:
        print("Env:", " ".join(f"{key}={value}" for key, value in sorted(env_overrides.items())))
    print("=" * 78)
    started = time.time()

    step_env = env.copy()
    if env_overrides:
        step_env.update(env_overrides)

    result = subprocess.run(command, env=step_env)
    elapsed = time.time() - started

    if result.returncode != 0:
        raise RuntimeError(f"Step failed: {label} (exit code {result.returncode})")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] DONE: {label} ({elapsed:.1f}s)")


def main() -> int:
    args = parse_args()

    project_root = Path(__file__).resolve().parent.parent
    python_exe = sys.executable

    logs_dir = project_root / "outputs" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    lock_path = project_root / "data" / "processed" / ".daily_pipeline.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if lock_path.exists():
        age_minutes = (time.time() - lock_path.stat().st_mtime) / 60.0
        if age_minutes >= STALE_LOCK_MINUTES:
            print(
                "Removing stale lock file at",
                lock_path,
                f"(age: {age_minutes:.1f} minutes).",
            )
            lock_path.unlink()
        else:
            print(
                "Existing lock file found at",
                lock_path,
                f"(age: {age_minutes:.1f} minutes).",
            )
            print("If no run is active, delete the lock file and retry.")
            return 1

    if lock_path.exists():
        print(
            "Existing lock file found at",
            lock_path,
            "(unable to remove it automatically).",
        )
        print("If no run is active, delete the lock file and retry.")
        return 1

    lock_path.write_text(datetime.now().isoformat(), encoding="utf-8")

    log_file = logs_dir / f"daily_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    print(f"Project root: {project_root}")
    print(f"Python exe  : {python_exe}")
    print(f"Log file    : {log_file}")

    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"

    steps: list[tuple[str, list[str], dict[str, str] | None]] = []

    if not args.skip_scrape:
        scrape_cmd = [
            python_exe,
            str(project_root / "scrapper" / "nepse_scraper.py"),
            "--source",
            args.source,
            "--delay",
            str(args.delay),
        ]
        # Forward optional start-date to the scraper so automation can control the global window
        if args.start_date:
            scrape_cmd.extend(["--start-date", args.start_date])
        if args.symbols.strip():
            scrape_cmd.extend(["--symbols", args.symbols.strip()])
        if args.skip_parquet:
            scrape_cmd.append("--skip-parquet")

        steps.append(("Scrape latest NEPSE data", scrape_cmd, None))

    prep_scripts = [
        "01_data_audit.py",
        "02_data_cleaning.py",
        "03_feature_engineering.py",
        "03b_fix_infinities.py",
        "04_label_construction.py",
        "05_walk_forward_setup.py",
    ]

    model_scripts = [
        "06_train_model.py",
        "06b_train_sell_model.py",
        "07_backtest.py",
        "08_reporting.py",
    ]

    for script_name in prep_scripts:
        steps.append(
            (
                f"Run {script_name}",
                [python_exe, str(project_root / "src" / script_name)],
                None,
            )
        )

    requested_family = "random_forest" if args.model_family == "rf" else args.model_family
    model_families = ["xgboost", "random_forest"] if requested_family == "both" else [requested_family]

    for family in model_families:
        family_env = {"MODEL_FAMILY": family}
        family_label = "Random Forest" if family == "random_forest" else "XGBoost"
        for script_name in model_scripts:
            steps.append(
                (
                    f"Run {script_name} ({family_label})",
                    [python_exe, str(project_root / "src" / script_name)],
                    family_env,
                )
            )

    started_all = time.time()
    exit_code = 0

    try:
        with log_file.open("w", encoding="utf-8") as fh:
            fh.write(f"Daily pipeline started: {datetime.now().isoformat()}\n")
            fh.write(f"Python: {python_exe}\n")
            fh.write(f"Project root: {project_root}\n")
            fh.write("\n")

        for label, command, env_overrides in steps:
            run_step(label, command, env, env_overrides)
            with log_file.open("a", encoding="utf-8") as fh:
                fh.write(f"SUCCESS: {label} at {datetime.now().isoformat()}\n")

        total = time.time() - started_all
        print("\n" + "#" * 78)
        print(f"PIPELINE SUCCESS in {total/60:.1f} minutes")
        print("#" * 78)

    except Exception as exc:
        exit_code = 1
        print("\n" + "#" * 78)
        print("PIPELINE FAILED")
        print(str(exc))
        print("#" * 78)
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(f"FAILED at {datetime.now().isoformat()}: {exc}\n")

    finally:
        if lock_path.exists():
            lock_path.unlink()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
