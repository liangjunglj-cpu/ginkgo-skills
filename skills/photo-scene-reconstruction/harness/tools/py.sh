#!/bin/bash
# run a tool with the image deps:  tools/py.sh tools/x.py args...
export UV_LINK_MODE=copy
exec uv run -q --with opencv-python-headless --with numpy --with pillow python "$@"
