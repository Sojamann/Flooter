#!/bin/sh

. venv/bin/activate

for file in $(find tests/ -name *.py | cut -d / -f 2); do
    echo $file
    #python $file
    python -m unittest $file ||  true
    echo "python -m unittest tests.$file"
done;

