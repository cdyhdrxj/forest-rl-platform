export const SLIDER_CONFIG = {

  "Непрерывная 2D": {

    "Тропы": {
      "Алгоритм": [
        { param: "learning_rate",     label: "Скор. обучения",  default: 0.0003, min: 0.00001, max: 0.01,  step: 0.00001 },
        { param: "gamma",             label: "Гамма (γ)",       default: 0.99,   min: 0.9,     max: 0.999, step: 0.001   },
        { param: "max_steps",         label: "Макс. шагов",     default: 240,    min: 50,      max: 1000,  step: 10      },
        { param: "tau",               label: "Тау",             default: 0.005,  min: 0.001,   max: 0.1,   step: 0.001,  algoOnly: ["SAC"] },
        { param: "goal_reward",       label: "Награда за цель", default: 50,     min: 10,      max: 100,   step: 5       },
        { param: "collision_penalty", label: "Штраф столкн.",   default: 0.3,    min: 0,       max: 5,     step: 0.1     },
        { param: "step_penalty",      label: "Штраф за шаг",    default: 0,      min: 0,       max: 1,     step: 0.01    },
        { param: "terrain_penalty",   label: "Штраф рельефа",   default: 0.03,   min: 0,       max: 1,     step: 0.01    },
      ],
      "Карта": [
        { param: "grid_size",        label: "Размер сетки", default: 12, min: 5, max: 20,  step: 1    },
        { param: "obstacle_density", label: "Препятствия",  default: 0.12, min: 0, max: 0.4, step: 0.01 },
      ],
      "Робот": [
        { param: "action_scale", default: 1.0, min: 0.1,   max: 5,    step: 0.1,   label: "Масштаб действий" },
        { param: "max_speed",    default: 50,  min: 1,     max: 200,  step: 1,     label: "Макс. скорость" },
        { param: "accel",        default: 40,  min: 1,     max: 100,  step: 1,     label: "Разгон" },
        { param: "damping",      default: 0.6, min: 0.01,  max: 0.99, step: 0.01,  label: "Торможение" },
        { param: "dt",           default: 0.01,min: 0.001, max: 0.05, step: 0.001, label: "Шаг физики" },
      ],
    },
  },

  "Дискретная": {

    "Патруль": {
      "Алгоритм": [
        // Гиперпараметры из research-скриптов (16x16_forest/train_{ppo,dqn,drqn}_v3.py).
        // Служебные параметры (device, cpu_cores_num, features_dim, normalize_rewards,
        // use_cnn, common_seed, verbose, torch_compile/amp) фиксированы в коде сервиса
        // и здесь не выводятся. total_timesteps и seed — во вкладке «Конфигурации».
        // n_envs не выводится: при включённой визуализации обучения он форсится в 1.

        // Общие параметры (все алгоритмы)
        { param: "learning_rate",   label: "Скор. обучения", default: 0.0003,  min: 0.00001, max: 0.01,   step: 0.00001 },
        { param: "gamma",           label: "Гамма (γ)",      default: 0.999,   min: 0.9,    max: 0.9999,   step: 0.0001 },

        // PPO
        { param: "n_steps",    label: "Шагов роллаута",  default: 512,  min: 64,  max: 2048, step: 64,   type: "int", algoOnly: ["PPO"] },
        { param: "batch_size", label: "Батч",             default: 256,  min: 64,  max: 1024, step: 32,   type: "int", algoOnly: ["PPO"] },
        { param: "n_epochs",   label: "Эпох обновления",  default: 10,   min: 1,   max: 20,   step: 1,    type: "int", algoOnly: ["PPO"] },
        { param: "clip_range", label: "Клиппинг (ε)",     default: 0.2,  min: 0.1, max: 0.4,  step: 0.05,             algoOnly: ["PPO"] },
        { param: "ent_coef",   label: "Коэф. энтропии",   default: 0.01, min: 0,   max: 0.1,  step: 0.005,            algoOnly: ["PPO"] },

        // DQN
        { param: "batch_size",             label: "Батч",              default: 256,    min: 32,    max: 512,    step: 32,    type: "int", algoOnly: ["DQN"] },
        { param: "buffer_size",            label: "Размер буфера",     default: 750000, min: 10000, max: 2000000,step: 10000, type: "int", algoOnly: ["DQN"] },
        { param: "learning_starts",        label: "Старт обучения",    default: 25000,  min: 1000,  max: 100000, step: 1000,  type: "int", algoOnly: ["DQN"] },
        { param: "target_update_interval", label: "Обновл. цели",      default: 8000,   min: 500,   max: 20000,  step: 500,   type: "int", algoOnly: ["DQN"] },
        { param: "exploration_fraction",   label: "Доля исследования", default: 0.45,   min: 0.05,  max: 0.9,    step: 0.05,              algoOnly: ["DQN"] },
        { param: "exploration_final_eps",  label: "Финал. ε",          default: 0.05,   min: 0.01,  max: 0.2,    step: 0.01,              algoOnly: ["DQN"] },

        // DRQN (alt_drqn)
        { param: "batch_size",        label: "Батч",            default: 64,     min: 16,   max: 256,    step: 16,    type: "int", algoOnly: ["DRQN"] },
        { param: "lstm_hidden_size",  label: "LSTM размер",     default: 256,    min: 64,   max: 512,    step: 64,    type: "int", algoOnly: ["DRQN"] },
        { param: "unroll_length",     label: "Длина BPTT",      default: 25,     min: 5,    max: 100,    step: 5,     type: "int", algoOnly: ["DRQN"] },
        { param: "buffer_capacity",   label: "Ёмкость буфера",  default: 75000,  min: 5000, max: 300000, step: 5000,  type: "int", algoOnly: ["DRQN"] },
        { param: "learning_starts",   label: "Старт обучения",  default: 5000,   min: 500,  max: 50000,  step: 500,   type: "int", algoOnly: ["DRQN"] },
        { param: "epsilon_decay_steps",label: "Затух. ε (шагов)",default: 300000, min: 50000,max: 1000000,step: 50000, type: "int", algoOnly: ["DRQN"] },
        { param: "epsilon_final",     label: "Финал. ε",        default: 0.05,   min: 0.01, max: 0.2,    step: 0.01,              algoOnly: ["DRQN"] },
      ],

      // Единая вкладка генерации сценария. Курированный набор параметров,
      // собирающих актуальный GridForestConfig (poacher_alt + reward_config).
      // Дефолты соответствуют эталону forest_16x16_v3.json; всё, что здесь не
      // выведено, добивается дефолтами в buildPatrolPayload (patrol.js).
      "Генерировать сценарий": [
        // — Map —
        { param: "grid_size",        label: "grid_size",        default: 16,   min: 8,  max: 32,       step: 1,  type: "int" },
        { param: "map_seed",         label: "map_seed (0=random)", default: null, min: 0,  max: 99999999, step: 1,  type: "number" },
        { param: "passability_low",  label: "passability_low",  default: 0.9,  min: 0,  max: 1,        step: 0.05 },
        { param: "passability_high", label: "passability_high", default: 0.9,  min: 0,  max: 1,        step: 0.05 },
        { param: "impassable_prob",  label: "impassable_prob",  default: 0.1,  min: 0,  max: 0.5,      step: 0.01 },
        { param: "max_value",        label: "max_value",        default: 100,  min: 10, max: 1000,     step: 10, type: "int" },
        { param: "value_density",    label: "value_density",    default: 0.7,  min: 0,  max: 1,        step: 0.05 },

        // — Agent —
        { param: "agent_is_random_spawned", label: "agent.is_random_spawned", default: true, type: "bool" },
        { param: "spawn_min_passability",   label: "agent.spawn_min_passability", default: 1.0, min: 0, max: 1, step: 0.1 },
        { param: "agent_pos_x",             label: "agent.pos x (if not random)", default: 3, min: 0, max: 31, step: 1, type: "int" },
        { param: "agent_pos_y",             label: "agent.pos y (if not random)", default: 3, min: 0, max: 31, step: 1, type: "int" },

        // — Intruder (poacher_alt) —
        { param: "intruder_count",   label: "max_intruders",    default: 1,    min: 1,   max: 10,   step: 1,   type: "int" },
        { param: "m_plan",           label: "m_plan",           default: 175,  min: 10,  max: 1000, step: 5,   type: "int" },
        { param: "m_tool_power",     label: "m_tool_power",     default: 2.0,  min: 0.5, max: 100,  step: 0.5 },

        // — Rewards —
        { param: "m_catch",          label: "m_catch",          default: 350,  min: 0,     max: 1000, step: 10, type: "int" },
        { param: "m_exit_penalty",   label: "m_exit_penalty",   default: -250, min: -1000, max: 0,    step: 10, type: "int" },
        { param: "m_out",            label: "m_out",            default: 1.0,  min: 0,     max: 10,   step: 0.1 },
        { param: "m_stay",           label: "m_stay",           default: 0.3,  min: 0,     max: 5,    step: 0.1 },
        { param: "m_block",          label: "m_block",          default: 0.5,  min: 0,     max: 10,   step: 0.1 },
        { param: "exploration_reward", label: "exploration_reward", default: 0.1, min: 0, max: 2, step: 0.05 },
        { param: "useful_exp_reward",  label: "useful_exp_reward",  default: 0.3, min: 0, max: 2, step: 0.05 },

        // — Environment —
        { param: "max_steps",        label: "max_steps",        default: 256,  min: 50, max: 1000, step: 10, type: "int" },
        { param: "tau_min",          label: "tau_min",          default: 25,   min: 1,  max: 200, step: 5, type: "int" },
        { param: "tau_max",          label: "tau_max",          default: 75,   min: 5,  max: 500, step: 5, type: "int" },
      ],
    },

    "Посадка": {
      "Алгоритм": [
        { param: "learning_rate",      label: "Скор. обучения",      default: 0.0003, min: 0.00001, max: 0.01, step: 0.00001 },
        { param: "gamma",              label: "Гамма (γ)",           default: 0.99,   min: 0.9,     max: 0.999, step: 0.001  },
        { param: "max_steps",          label: "Макс. шагов",         default: 240,    min: 50,      max: 1000,  step: 10     },
        { param: "step_penalty",       label: "Штраф за шаг",        default: 0,      min: 0,       max: 1,     step: 0.01   },
        { param: "alpha_plant",        label: "Награда за посадку",  default: 4.0,    min: 0.5,     max: 10,    step: 0.1    },
        { param: "alpha_quality",      label: "Вес качества",        default: 2.0,    min: 0,       max: 5,     step: 0.1    },
        { param: "beta_move",          label: "Штраф движения",      default: 0.08,   min: 0,       max: 1,     step: 0.01   },
        { param: "beta_turn",          label: "Штраф поворота",      default: 0.04,   min: 0,       max: 1,     step: 0.01   },
        { param: "beta_invalid_plant", label: "Штраф плохой посадки",default: 0.6,    min: 0,       max: 2,     step: 0.01   },
      ],
      "Карта": [
        { param: "grid_size",            label: "Размер сетки",       default: 12, min: 5,    max: 20,  step: 1    },
        { param: "obstacle_density",     label: "Препятствия",        default: 0.12,min: 0,    max: 0.4, step: 0.01 },
        { param: "plantable_density",    label: "Засаживаемость",     default: 0.7, min: 0.1,  max: 1,   step: 0.01 },
        { param: "min_plant_distance",   label: "Мин. расстояние",    default: 1,   min: 0,    max: 3,   step: 1    },
        { param: "uniformity_radius",    label: "Радиус равномерн.",  default: 1,   min: 0,    max: 3,   step: 1    },
        { param: "target_density",       label: "Целевая плотн.",     default: 0.35, min: 0.05, max: 0.8, step: 0.01 },
        { param: "lambda_uniformity",    label: "Штраф равномерн.",   default: 3.0, min: 0,    max: 10,  step: 0.1  },
        { param: "lambda_underplanting", label: "Штраф недопосадки",  default: 1.5, min: 0,    max: 10,  step: 0.1  },
      ],
      "Робот": [
        { param: "initial_seedlings", label: "Саженцев на борту", default: 30, min: 5, max: 80, step: 1    },
        { param: "beta_stay",         label: "Штраф стояния",     default: 0.12,min: 0, max: 1,  step: 0.01 },
        { param: "beta_fail_move",    label: "Штраф неудачи хода",default: 0.25,min: 0, max: 2,  step: 0.01 },
      ],
    },
  },

  "3D симулятор": {
    "Тропы": {
      "Ландшафт": [
        { param: "mesh_height_multiplayer", label: "Множитель высоты", default: 1.0, min: 0.5, max: 5, step: 0.1, type: "number" },
        { param: "noise_scale",             label: "Масштаб шума",    default: 150.0, min: 0.001, max: 500.0, step: 0.1, type: "number" },
        { param: "seed",                    label: "Seed ландшафта",  default: 42,  min: 0,   max: 999999, step: 1, type: "number" },
        { param: "octaves",                 label: "Детализация слоёв шума",           default: 4,   min: 1,   max: 8,   step: 1, type: "int" },
        { param: "lacunarity",              label: "Частотный множитель между слоями",     default: 2.0, min: 1.5, max: 3.5, step: 0.1 },
        { param: "density",                 label: "Плотность появления объектов",           default: 10,   min: 0,   max: 100,   step: 1, type: "int" },
        { param: "max_view_dst",            label: "Размер ландшафта", default: 1, min: 1, max: 3, step: 1, type: "int" },
      ],
      "Робот": [
        { param: "robot_type", label: "Тип робота", type: "select", options: [0, 1], default: 0 },
        { param: "robot_position_x", label: "X", default: 0, type: "coordinates", group: "robot" },
        { param: "robot_position_y", label: "Y", default: 0, type: "coordinates", group: "robot" },
        { param: "robot_position_z", label: "Z", default: 0, type: "coordinates", group: "robot" },
        { param: "robot_rotation_y", label: "Поворот (Y)", default: 0, min: 0, max: 360, step: 15, type: "int" },
      ],
      "Цель": [
        { param: "target_position_x", label: "X", default: 0, type: "coordinates", group: "target" },
        { param: "target_position_y", label: "Y", default: 0, type: "coordinates", group: "target" },
        { param: "target_position_z", label: "Z", default: 0, type: "coordinates", group: "target" },
        { param: "radius", label: "Радиус цели", default: 1.0, min: 0.1, max: 1000.0, step: 0.1, type: "number" },
      ],
      "Алгоритм": [
        { param: "learning_rate",       label: "Скор. обучения",  default: 0.0003, min: 0.00001, max: 0.01,  step: 0.00001 },
        { param: "gamma",               label: "Гамма (γ)",       default: 0.99,   min: 0.9,     max: 0.999, step: 0.001 },
        { param: "max_steps",           label: "Макс. шагов",     default: 240,    min: 50,      max: 1000,  step: 10, type: "int" },
        { param: "goal_reward",         label: "Награда за цель", default: 50,     min: 10,      max: 100,   step: 5 },
        { param: "collision_penalty",   label: "Штраф столкн.",   default: 0.3,    min: 0,       max: 10,    step: 0.5 },
        { param: "step_penalty",        label: "Штраф за шаг",    default: 0,      min: 0,       max: 2,     step: 0.05 },
        { param: "terrain_penalty",     label: "Штраф рельефа",   default: 0.03,   min: 0,       max: 2,     step: 0.05 },
      ],
    },
  },
}