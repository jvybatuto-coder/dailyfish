#!/usr/bin/env bash
set -o errexit

cd myproject
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python create_live_admin.py