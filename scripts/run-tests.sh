#!/bin/bash
set -e
pytest -v --cov=src --cov=packages/core --cov-report=term-missing