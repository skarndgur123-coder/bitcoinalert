import yaml


def load_thresholds(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
