# Scenario Generator

Shared environment-generation module for the platform.

## Responsibilities

- accept a common generation request;
- choose a family generator by environment kind;
- apply task-specific overlays;
- validate the generated scenario;
- return a canonical generated-scenario object for runtime adapters.

## Main entrypoint

- `get_default_environment_generation_service()`

## Built-in support

- `grid`
- `continuous_2d`
- `simulator_3d`

## Current integrations

- `services/patrol_planning`
- `services/reforestation_planting`
- `services/trail_camar`
