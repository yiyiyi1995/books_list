#!/bin/sh
cd "$(dirname "$0")"
open http://127.0.0.1:8765
exec /usr/bin/python3 server.py
