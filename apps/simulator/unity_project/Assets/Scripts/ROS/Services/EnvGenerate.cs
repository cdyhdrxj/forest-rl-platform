using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Forest;

public class EnvGenerate : RosService<SetTerrainParamsRequest, SetTerrainParamsResponse>
{
    TerrainSize terrain;
    MapGenerator mapGenerator;

    [SerializeField] NoiseData noiseData;
    [SerializeField] TerData terData;
    [SerializeField] FoliageData foliageData;

    protected override void OnStart()
    {
        terrain = FindObjectOfType<TerrainSize>();
        mapGenerator = FindObjectOfType<MapGenerator>();
    }

    protected override SetTerrainParamsResponse HandleReset(SetTerrainParamsRequest request)
    {
        // Применяем параметры к ScriptableObject'ам
        ApplyNoiseData(request);
        ApplyTerData(request);
        ApplyFoliageData(request);

        // Регенерируем terrain с новыми параметрами
        terrain.Regenerate();

        return new SetTerrainParamsResponse
        {
            success = true,
            message = "Terrain regenerated successfully"
        };
    }

    private void ApplyNoiseData(SetTerrainParamsRequest request)
    {
        // Создаём новый экземпляр вместо изменения ассета
        NoiseData newNoiseData = ScriptableObject.CreateInstance<NoiseData>();
        newNoiseData.noise_scale = request.noise_scale;
        newNoiseData.seed = request.seed;
        newNoiseData.octaves = request.octaves;
        newNoiseData.persistance = request.persistance;
        newNoiseData.lacunarity = request.lacunarity;
        newNoiseData.offset = new Vector2(request.offset_x, request.offset_y);
        newNoiseData.normalizeMode = (Noise.NormalizeMode)request.noise_normalize_mode;

        // Заменяем в MapGenerator напрямую
        mapGenerator.noiseData = newNoiseData;
    }

    private void ApplyTerData(SetTerrainParamsRequest request)
    {
        TerData newTerData = ScriptableObject.CreateInstance<TerData>();
        newTerData.uniformScale = request.uniform_scale;
        newTerData.meshHeightMultiplayer = request.mesh_height_multiplayer;
        newTerData.maxViewDst = request.max_view_dst;
        // meshHeightCurve скопируй из старого
        newTerData.meshHeightCurve = terData.meshHeightCurve;

        mapGenerator.terData = newTerData;
    }

    private void ApplyFoliageData(SetTerrainParamsRequest request)
    {
        if (foliageData == null)
        {
            Debug.LogWarning("FoliageData is null");
            return;
        }

        if (foliageData.layers == null)
        {
            Debug.LogWarning("FoliageData layers are null");
            return;
        }

        int density = Mathf.Clamp(request.density, 0, 100);

        foreach (var layer in foliageData.layers)
        {
            layer.density = density;
        }

        foliageData.seed = request.seed;

        Debug.Log($"[EnvGenerate] Foliage density set to {density}");
    }
}