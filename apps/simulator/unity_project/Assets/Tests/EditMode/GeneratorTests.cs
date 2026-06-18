#if UNITY_EDITOR && UNITY_INCLUDE_TESTS
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

/// <summary>
/// Edit Mode тесты для Noise и MeshGenerator.
/// Путь в проекте: Assets/Tests/EditMode/NoiseTests.cs
/// </summary>
public class GeneratorTests
{
    // ===== Noise.GenerateNoiseMap =====

    [Test]
    public void GenerateNoiseMap_CorrectSize()
    {
        int width = 10, height = 10;
        float[,] map = Noise.GenerateNoiseMap(
            width, height, seed: 42, scale: 100f,
            octaves: 4, persistance: 0.5f, lacunarity: 2f,
            offset: Vector2.zero,
            normalizeMode: Noise.NormalizeMode.Global);

        Assert.AreEqual(width,  map.GetLength(0));
        Assert.AreEqual(height, map.GetLength(1));
    }

    [Test]
    public void GenerateNoiseMap_ValuesInRange()
    {
        float[,] map = Noise.GenerateNoiseMap(
            20, 20, seed: 0, scale: 80f,
            octaves: 4, persistance: 0.5f, lacunarity: 2f,
            offset: Vector2.zero,
            normalizeMode: Noise.NormalizeMode.Global);

        foreach (float v in map)
            Assert.GreaterOrEqual(v, 0f, "Значение меньше 0");
    }

    [Test]
    public void GenerateNoiseMap_SameSeed_ProducesSameMap()
    {
        var args = (seed: 123, scale: 100f, octaves: 4,
                    persistance: 0.5f, lacunarity: 2f);

        float[,] map1 = Noise.GenerateNoiseMap(
            15, 15, args.seed, args.scale, args.octaves,
            args.persistance, args.lacunarity,
            Vector2.zero, Noise.NormalizeMode.Global);

        float[,] map2 = Noise.GenerateNoiseMap(
            15, 15, args.seed, args.scale, args.octaves,
            args.persistance, args.lacunarity,
            Vector2.zero, Noise.NormalizeMode.Global);

        for (int y = 0; y < 15; y++)
            for (int x = 0; x < 15; x++)
                Assert.AreEqual(map1[x, y], map2[x, y],
                    $"Расхождение в [{x},{y}]");
    }

    [Test]
    public void GenerateNoiseMap_DifferentSeeds_ProduceDifferentMaps()
    {
        float[,] map1 = Noise.GenerateNoiseMap(
            15, 15, seed: 1, scale: 100f, octaves: 4,
            persistance: 0.5f, lacunarity: 2f,
            Vector2.zero, Noise.NormalizeMode.Global);

        float[,] map2 = Noise.GenerateNoiseMap(
            15, 15, seed: 999, scale: 100f, octaves: 4,
            persistance: 0.5f, lacunarity: 2f,
            Vector2.zero, Noise.NormalizeMode.Global);

        bool different = false;
        for (int y = 0; y < 15; y++)
            for (int x = 0; x < 15; x++)
                if (!Mathf.Approximately(map1[x, y], map2[x, y]))
                    different = true;

        Assert.IsTrue(different,
            "Карты с разными seed должны отличаться");
    }

    [Test]
    public void GenerateNoiseMap_ZeroScale_DoesNotThrow()
    {
        Assert.DoesNotThrow(() =>
        {
            Noise.GenerateNoiseMap(
                10, 10, seed: 0, scale: 0f, octaves: 2,
                persistance: 0.5f, lacunarity: 2f,
                Vector2.zero, Noise.NormalizeMode.Local);
        });
    }

    [Test]
    public void GenerateNoiseMap_LocalMode_ValuesNormalized()
    {
        float[,] map = Noise.GenerateNoiseMap(
            20, 20, seed: 7, scale: 100f, octaves: 4,
            persistance: 0.5f, lacunarity: 2f,
            Vector2.zero, Noise.NormalizeMode.Local);

        float min = float.MaxValue, max = float.MinValue;
        foreach (float v in map)
        {
            if (v < min) min = v;
            if (v > max) max = v;
        }

        Assert.AreEqual(0f, min, 0.0001f,
            "Минимум должен быть 0 в Local режиме");
        Assert.AreEqual(1f, max, 0.0001f,
            "Максимум должен быть 1 в Local режиме");
    }

    // ===== MeshGenerator.GenerateTerrainMesh =====

    [Test]
    public void GenerateTerrainMesh_LOD0_CorrectVertexCount()
    {
        int size = 241; // mapChunkSize + 2
        float[,] heightMap = new float[size, size];

        AnimationCurve curve = AnimationCurve.Linear(0, 0, 1, 1);
        MeshData meshData = MeshGenerator.GenerateTerrainMesh(
            heightMap, heightMultiplayer: 10f,
            _heightCurve: curve, levelOfDetail: 0);

        Mesh mesh = meshData.CreateMesh();

        // При LOD=0 и size=241: verticesPerLine = 239
        Assert.AreEqual(239 * 239, mesh.vertices.Length);
    }

    [Test]
    public void GenerateTerrainMesh_FlatMap_AllVerticesSameHeight()
    {
        int size = 11;
        float[,] heightMap = new float[size, size]; // все 0

        AnimationCurve curve = AnimationCurve.Linear(0, 0, 1, 1);
        MeshData meshData = MeshGenerator.GenerateTerrainMesh(
            heightMap, heightMultiplayer: 10f,
            _heightCurve: curve, levelOfDetail: 0);

        Mesh mesh = meshData.CreateMesh();

        foreach (Vector3 v in mesh.vertices)
            Assert.AreEqual(0f, v.y, 0.001f,
                "Все вершины плоской карты должны быть на высоте 0");
    }

    [Test]
    public void GenerateTerrainMesh_HeightMultiplier_ScalesVertices()
    {
        int size = 11;
        float[,] heightMap = new float[size, size];
        for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
                heightMap[x, y] = 1f; // все на максимальной высоте

        AnimationCurve curve = AnimationCurve.Linear(0, 0, 1, 1);

        MeshData mesh5  = MeshGenerator.GenerateTerrainMesh(
            heightMap, 5f,  curve, 0);
        MeshData mesh10 = MeshGenerator.GenerateTerrainMesh(
            heightMap, 10f, curve, 0);

        float h5  = mesh5.CreateMesh().vertices[0].y;
        float h10 = mesh10.CreateMesh().vertices[0].y;

        Assert.AreEqual(h5 * 2f, h10, 0.001f,
            "Высота должна масштабироваться пропорционально multiplier");
    }

    [Test]
    public void GenerateTerrainMesh_HasNormals()
    {
        int size = 11;
        float[,] heightMap = new float[size, size];

        AnimationCurve curve = AnimationCurve.Linear(0, 0, 1, 1);
        MeshData meshData = MeshGenerator.GenerateTerrainMesh(
            heightMap, 10f, curve, 0);

        Mesh mesh = meshData.CreateMesh();

        Assert.IsNotNull(mesh.normals);
        Assert.Greater(mesh.normals.Length, 0,
            "Меш должен содержать нормали");
    }
}
#endif