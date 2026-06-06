#!/bin/bash
set -e
cd packages/core
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*