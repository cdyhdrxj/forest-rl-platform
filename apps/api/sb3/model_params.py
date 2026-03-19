PPO_DEFAULTS = {
    "learning_rate": 3e-4,
    "gamma": 0.99,
    "n_steps": 1024,
    "batch_size": 64,
    "n_epochs": 10,
    "clip_range": 0.2,
}

SAC_DEFAULTS = {
    "learning_rate": 3e-4,
    "gamma": 0.99,
    "buffer_size": 1_000_000,
    "batch_size": 256,
    "tau": 0.005,
}

A2C_DEFAULTS = {
    "learning_rate": 7e-4,
    "gamma": 0.99,
    "n_steps": 5,
}

ALGO_DEFAULTS = {
    "ppo": PPO_DEFAULTS,
    "sac": SAC_DEFAULTS,
    "a2c": A2C_DEFAULTS,
}