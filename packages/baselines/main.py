from scenario_loader import load_scenario
from experiment import run_experiments

reward_config = {
    "W_STEP": 0.01,
    "W_HEIGHT": 1.0,
    "W_COLLISION_BUSH": 1.0,
    "W_COLLISION_TREE": 50.0
}

scenario = load_scenario("scenario.json")

results = run_experiments(scenario, reward_config, n=50)

print(results)
