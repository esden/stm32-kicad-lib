#!/bin/sh

git submodule init
git submodule update

cd script
./kicadlibgen.py
cd -
