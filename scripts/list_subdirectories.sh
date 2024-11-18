#!/bin/bash

# Get the list of subdirectories
list=$(find . -maxdepth 1 -type d ! -path . | sed 's|./||' | paste -sd "," -)
# Print the list (optional)
echo "$list" > list

