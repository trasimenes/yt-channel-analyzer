import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data.json')


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"competitors": {}}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
