using UnityEngine;
using System.Collections;
using System;
using System.Threading;
using System.Collections.Generic;

public class MapGenerator : MonoBehaviour
{
    public enum DrawMode {NoiseMap, Mesh}
    public DrawMode drawMode;

    public TerData terData;
    public NoiseData noiseData;
    public TexData texData;

    public Material terrainMaterial;

    public const int mapChunkSize = 239;
    [Range(0, 6)]
    public int levelOfDetail;

    public bool auto_update;

    Queue<MapThreadInfo<MapData>> mapDataThreadingInfoQueue = new Queue<MapThreadInfo<MapData>>();
    Queue<MapThreadInfo<MeshData>> meshDataThreadingInfoQueue = new Queue<MapThreadInfo<MeshData>>();

    public void DrawMapInEditor()
    {
        MapData mapData = GenerateMapData(Vector2.zero);

        MapDisplay display = FindObjectOfType<MapDisplay>();
        if (!display) return;

        switch(drawMode)
        {
            case DrawMode.NoiseMap:
                display.DrawTexture(TextureGenerator.TextureFromHeightMap(mapData.height_map));
                break;
            case DrawMode.Mesh:
                display.DrawMesh(MeshGenerator.GenerateTerrainMesh(mapData.height_map, terData.meshHeightMultiplayer, terData.meshHeightCurve, levelOfDetail));
                break;
        }
    }

    public void ClearAndReset()
    {
        lock(mapDataThreadingInfoQueue)
        {
            mapDataThreadingInfoQueue.Clear();
        }
        lock(meshDataThreadingInfoQueue)
        {
            meshDataThreadingInfoQueue.Clear();
        }
    }

    public void RequestMapData(Vector2 center, Action<MapData> callback)
    {
        ThreadStart threadStart = delegate
        {
            MapDataThread(center, callback);
        };

        new Thread(threadStart).Start();
    }

    void MapDataThread(Vector2 center, Action<MapData> callback)
    {
        MapData mapData = GenerateMapData(center);
        lock(mapDataThreadingInfoQueue) {
            mapDataThreadingInfoQueue.Enqueue(new MapThreadInfo<MapData>(callback, mapData));
        }
    }

    public void RequestMeshData(MapData mapData, Action<MeshData> callback)
    {
        ThreadStart threadStart = delegate
        {
            MeshDataThread(mapData, callback);
        };

        new Thread(threadStart).Start();      
    }

    void MeshDataThread(MapData mapData, Action<MeshData> callback)
    {
        MeshData meshData = MeshGenerator.GenerateTerrainMesh(mapData.height_map, terData.meshHeightMultiplayer, terData.meshHeightCurve, levelOfDetail);
        lock(meshDataThreadingInfoQueue) {
            meshDataThreadingInfoQueue.Enqueue(new MapThreadInfo<MeshData>(callback, meshData));
        }
    }

    void Update()
    {
        if (mapDataThreadingInfoQueue.Count > 0)
        {
            for (int i = 0; i < mapDataThreadingInfoQueue.Count; i++)
            {
                MapThreadInfo<MapData> threadInfo = mapDataThreadingInfoQueue.Dequeue();
                texData.UpdateMeshHeights(terrainMaterial, terData.minHeight, terData.maxHeight);
                threadInfo.callback(threadInfo.parameter);
            }
        }
        if (meshDataThreadingInfoQueue.Count > 0)
        {
            for (int i = 0; i < meshDataThreadingInfoQueue.Count; i++)
            {
                MapThreadInfo<MeshData> threadInfo = meshDataThreadingInfoQueue.Dequeue();
                threadInfo.callback(threadInfo.parameter);
            }
        }
    }

    MapData GenerateMapData(Vector2 center) {
        float[,] noise_map = Noise.GenerateNoiseMap(mapChunkSize + 2, mapChunkSize + 2, noiseData.seed, noiseData.noise_scale, noiseData.octaves, noiseData.persistance, noiseData.lacunarity, center + noiseData.offset, noiseData.normalizeMode);

        // for (int y = 0; y < mapChunkSize; y++)
        // {
        //     for (int x = 0; x < mapChunkSize; x++)
        //     {
        //     }
        // }

        return new MapData(noise_map);
    }
}

struct MapThreadInfo<T> 
{
    public readonly Action<T> callback;
    public readonly T parameter;
    
    public MapThreadInfo(Action<T> callback, T parameter)
    {
        this.callback = callback;
        this.parameter = parameter;
    }
}

[System.Serializable]
public struct TerrainType
{
    public string name;
    public float height;
    public Color color;
}

public struct MapData
{
    public readonly float[,] height_map;

    public MapData(float[,] height_map)
    {
        this.height_map = height_map;
    }
}