# Information Workspace

This directory holds external-source pull code, tests, and pulled artifacts.

## Layout

- `cards/`: pulled card metadata and image assets
- `rules/`: pulled rules artifacts
- `pull_sources.py`: active support-slice source-pull entry point
- `tests/`: ingestion workflow tests

## Constraints

- Pull scripts and tests for external information should live under `information/`.
- Card metadata files and card image files must be stored in separate subdirectories.
- One file per card metadata record and one file per card image asset.
- Raw source presence does not imply gameplay support.

## Current Workflow

- Run `python information/pull_sources.py` to refresh the active support-slice card artifacts and the current rules snapshot.
- Run `python -m unittest discover -s information/tests` to validate the pull workflow behavior.
