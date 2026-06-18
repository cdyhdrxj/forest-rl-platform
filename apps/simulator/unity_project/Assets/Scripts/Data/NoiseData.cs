using UnityEngine;
using System.Collections;

[CreateAssetMenu()]
public class NoiseData : ScriptableObject
{
    public Noise.NormalizeMode normalizeMode;

    public float noise_scale;

    public int seed;

    public int octaves;
    [Range(0, 1)]
    public float persistance;
    public float lacunarity;

    public Vector2 offset;

    private void OnValidate()
    {
        if (lacunarity < 1) lacunarity = 1;
        if (octaves < 0) octaves = 0;
    }
}
