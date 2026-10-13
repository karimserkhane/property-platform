"""Explicit operator commands; starting services never applies business migrations."""

import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Property Platform ingestion orchestration")
    parser.add_argument("command", choices=("serve", "check", "datasets"))
    args = parser.parse_args()
    if args.command == "serve":
        from .deployments import serve

        serve()
    elif args.command == "check":
        from .runtime import invoke_domain

        print(json.dumps(invoke_domain({"operation": "check"}), indent=2))
    else:
        from dataclasses import asdict

        from .registry import DATASETS

        print(json.dumps([asdict(dataset) for dataset in DATASETS], indent=2))


if __name__ == "__main__":
    main()
