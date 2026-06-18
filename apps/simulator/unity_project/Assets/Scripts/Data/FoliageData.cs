using UnityEngine;
using System.Collections.Generic;

[CreateAssetMenu()]
public class FoliageData : ScriptableObject
{
    public int seed = 42;

    public FoliageLayer[] layers;

    private void OnValidate()
    {
        foreach (var layer in layers)
        {
            if (layer.density < 0) layer.density = 0;
            if (layer.density > 100) layer.density = 100;
            if (layer.minScale < 0.01f) layer.minScale = 0.01f;
            if (layer.maxScale < layer.minScale) layer.maxScale = layer.minScale;
        }
    }

    [System.Serializable]
    public class FoliageLayer
    {
        public string name = "Layer";

        [Tooltip("Prefabs for this layer — one will be chosen randomly per spawn point")]
        public GameObject[] prefabs;

        [Range(0f, 100f)]
        [Tooltip("Spawn probability per grid cell (0 = none, 1 = maximum)")]
        public int density = 1;

        [Tooltip("Minimum height (0–1 normalized) at which this layer can spawn")]
        [Range(0f, 1f)]
        public float minHeightThreshold = 0f;

        [Tooltip("Maximum height (0–1 normalized) at which this layer can spawn")]
        [Range(0f, 1f)]
        public float maxHeightThreshold = 1f;

        [Tooltip("Minimum slope angle (degrees) allowed for spawning")]
        [Range(0f, 90f)]
        public float minSlopeAngle = 0f;

        [Tooltip("Maximum slope angle (degrees) allowed for spawning")]
        [Range(0f, 90f)]
        public float maxSlopeAngle = 45f;

        public float minScale = 0.8f;
        public float maxScale = 1.2f;

        [Tooltip("Randomize Y rotation")]
        public bool randomYRotation = true;
    }
}
