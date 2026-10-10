"""QUASAR: Quantitative Unique Alpine Ski Altitude Routing
Main execution entry point for Qollab Hackathon (https://qollab.xyz/projects).

Official Attribution: This effort is supported by Qollab & IonQ
Track: Student Track | Node: Colorado School of Mines | Theme: Quantum Impact
License: MIT License
"""

import sys
import os
from pathlib import Path
import argparse

# Ensure current repository root is on sys.path (safe for web/exec environments without __file__)
REPO_ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd().resolve()
for _path in [REPO_ROOT, Path.cwd().resolve()]:
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from quasar.main import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="QUASAR: Quantitative Unique Alpine Ski Altitude Routing (Winter Park Resort)"
    )
    parser.add_argument(
        "--resort",
        type=str,
        default="winter_park",
        choices=["winter_park", "sample"],
        help="Target alpine resort topology dataset (default: winter_park)",
    )
    parser.add_argument(
        "--time",
        type=float,
        default=45.0,
        help="Target ski session duration in minutes (default: 45.0 min)",
    )
    parser.add_argument(
        "--p",
        type=int,
        default=1,
        help="QAOA circuit variational depth p (default: 1)",
    )
    parser.add_argument(
        "--run-baselines",
        action="store_true",
        help="Also run multi-hour classical trajectory baselines (1h, 2h, 4h)",
    )

    args = parser.parse_args()

    # Execute primary QUASAR Quantum Pipeline
    run_pipeline(resort_name=args.resort, target_time_min=args.time, depth_p=args.p)

    # Optional extended baselines if flagged
    if args.run_baselines:
        print("\n" + "=" * 90)
        from verify_baselines import verify_winter_park_baselines
        verify_winter_park_baselines()


if __name__ == "__main__":
    main()
