#!/usr/bin/env bash
set -e

echo "Running Dristik 2.0 Test Suite..."
cd backend
pytest tests/ -v
