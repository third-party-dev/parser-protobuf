#!/usr/bin/env bash

export PS1_TAG="(ml-venv) "
export PS1="${PS1_TAG}${PS1:-\$ }"

if [ ! -f "./ml-venv" ]; then
  python3 -m venv ./ml-venv
  [ $? -ne 0 ] && { echo "Failed to create venv"; exit 1; }
fi
source ./ml-venv/bin/activate

pip show protobuf &>/dev/null || pip install protobuf
pip show numpy &>/dev/null || pip install numpy

exec bash -i
