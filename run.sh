#!/bin/bash

CD=$(dirname "$(readlink -f "$0")")  # "

PYTHON=python

[[ -e "$CD/bin/_props.sh" ]] && . "$CD/bin/_props.sh"
[[ -e "$CD/_props.sh" ]] && . "$CD/_props.sh"


"$PYTHON" "$CD/main.py" "$@"
