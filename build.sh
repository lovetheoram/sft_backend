#!/usr/bin/env bash
# exit on error
set -o errexit

echo "==> 📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> 🎨 Collecting static files..."
python manage.py collectstatic --no-input

echo "==> 🗄️ Running Database Migrations..."
python manage.py migrate
