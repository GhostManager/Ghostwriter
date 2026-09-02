import yaml

def load_config(file_path: str) -> dict:
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config