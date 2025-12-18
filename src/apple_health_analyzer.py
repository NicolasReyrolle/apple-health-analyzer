#!/usr/bin/env python3
"""
Apple Health Analyzer CLI

A command-line interface for analyzing Apple Health data.
"""

import sys
import argparse
from typing import Dict, Any

from src.export_parser import ExportParser

def parse_cli_arguments() -> Dict[str, Any]:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyse data from an Apple Health export."
    )
    parser.add_argument('export_file', type=str, help='Path to the Apple Health export zip file')

    args = parser.parse_args()

    return {'export_file': args.export_file}


def main() -> None:
    """Main entry point for the CLI application."""
    result = parse_cli_arguments()
    print(f"Processing {result['export_file']}")

    with ExportParser(result['export_file']) as parser:
        parser.parse()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
