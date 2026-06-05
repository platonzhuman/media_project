#!/bin/bash
set -e
mkdir -p docs/_generated
cp docs/diagrams/*.mmd docs/_generated/
cp docs/diagrams/*.puml docs/_generated/
echo "Docs built in docs/_generated/"