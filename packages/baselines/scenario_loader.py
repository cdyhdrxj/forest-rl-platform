import numpy as np
import json

def load_scenario(path):
    with open(path, "r") as f:
        return json.load(f)


def load_layers(scenario):
    layers = scenario["version"]["layers"]

    elevation = None
    obstacles = None

    for layer in layers:
        if layer["layer_type"] == "elevation":
            elevation = np.load(layer["file_uri"])

        elif layer["layer_type"] == "obstacles":
            obstacles = np.load(layer["file_uri"])

    if elevation is None or obstacles is None:
        raise ValueError("Не найдены необходимые слои")

    return elevation, obstacles
