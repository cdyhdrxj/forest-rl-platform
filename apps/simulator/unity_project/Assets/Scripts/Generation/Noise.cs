using UnityEngine;
using System.Collections;

public static class Noise 
{

    public enum NormalizeMode {Local, Global};

    public static float[,] GenerateNoiseMap(int width, int height, int seed, float scale, int octaves, float persistance, float lacunarity, Vector2 offset, NormalizeMode normalizeMode) {
        float[,] noise_map = new float [width, height];

        System.Random prng = new System.Random(seed);
        Vector2[] octaveOffsets = new Vector2[octaves];

        float maxPossibleHeight = 0;
        float amplitude = 1;
        float frequency = 1;

        for (int i = 0; i < octaves; i++)
        {
            float offsetX = prng.Next(-10000, 10000) + offset.x;
            float offsetY = prng.Next(-10000, 10000) - offset.y;
            octaveOffsets[i] = new Vector2(offsetX, offsetY);

            maxPossibleHeight += amplitude;
            amplitude *= persistance;
        }

        if (scale <= 0) {
            scale = 0.0001f;
        }

        float max_local_height = float.MinValue;
        float min_local_height = float.MaxValue;

        float half_width = width / 2f;
        float half_height = height / 2f;

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                amplitude = 1;
                frequency = 1;
                float noise_height = 0;

                for (int i = 0; i < octaves; i++)
                {
                    float sampleX = (x-half_width + octaveOffsets[i].x) / scale * frequency;
                    float sampleY = (y-half_height + octaveOffsets[i].y) / scale * frequency;

                    float perlin_val = Mathf.PerlinNoise(sampleX, sampleY)*2-1;  
                    noise_height += perlin_val * amplitude;

                    amplitude *= persistance;
                    frequency *= lacunarity;
                }

                if (noise_height > max_local_height)
                {
                    max_local_height = noise_height;
                } else if (noise_height < min_local_height) {
                    min_local_height = noise_height; 
                }

                noise_map[x, y] = noise_height; 
            }
        }

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++)
            {
                switch(normalizeMode)
                {
                    case NormalizeMode.Local:
                        noise_map[x,y] = Mathf.InverseLerp(min_local_height, max_local_height, noise_map[x,y]);
                    break;
                    case NormalizeMode.Global:
                        float normalizeHeight = (noise_map[x, y] + 1) / maxPossibleHeight;
                        noise_map[x,y] = Mathf.Clamp(normalizeHeight, 0, int.MaxValue);
                    break;
                }
            }
        }

        return noise_map;
    }
}
