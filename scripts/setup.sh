#!/bin/bash
set -e
python -m pip install --upgrade pip setuptools wheel
pip install -e "./packages/core"
pip install -e ".[dev]"