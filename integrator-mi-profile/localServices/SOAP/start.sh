#!/bin/bash
cd "$(dirname "$0")"
echo "Starting SOAP Arithmetic Service on http://localhost:8080/"
python3 service.py
