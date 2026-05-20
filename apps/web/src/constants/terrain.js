import { Theme } from "./colors"

export function buildTerrainPayload(params) {
  return {
    map_config: {
      mesh_height_multiplayer: params.mesh_height_multiplayer,
      noise_scale:             params.noise_scale,
      seed:                    params.seed ?? null,
      octaves:                 params.octaves,
      lacunarity:              params.lacunarity,
      max_view_dst:            params.max_view_dst,
    },

    robot_config: {
      type: params.robot_type,
      pos: [
        params.robot_position_x,
        params.robot_position_y,
        params.robot_position_z,
      ],
      rotation_y: params.robot_rotation_y,
    },

    target_config: {
      pos: [
        params.target_position_x,
        params.target_position_y,
        params.target_position_z,
      ],
      radius: params.radius,
    },
  }
}
