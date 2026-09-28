#!/bin/bash
# helper: run a python file against the site via bench console
set -e
F="$1"
docker exec -i frappe_docker-backend-1 bench --site frontend console < "$F"
