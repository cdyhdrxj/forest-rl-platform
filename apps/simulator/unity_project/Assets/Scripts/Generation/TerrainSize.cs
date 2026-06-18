using UnityEngine;
using System.Collections.Generic;

public class TerrainSize : MonoBehaviour
{
    const float viewerMoveTresholdForChunksUpdate = 25f;
    const float sqrViewerMoveTresholdForChunkUpdate =
        viewerMoveTresholdForChunksUpdate *
        viewerMoveTresholdForChunksUpdate;

    public Transform viewer;
    public Material mapMaterial;

    [Header("Foliage")]
    public FoliageData foliageData;

    public static Vector2 viewerPosition;

    Vector2 viewerPositionOld;

    static MapGenerator mapGenerator;

    int chunkSize;
    int chunkVisibleInViewDst;

    Dictionary<Vector2, TerrainChunk> terrainChunkDictionary =
        new Dictionary<Vector2, TerrainChunk>();

    static List<TerrainChunk> terrainChunksVisibleLastUpdate =
        new List<TerrainChunk>();

    static Queue<TerrainChunk> foliageSpawnQueue =
        new Queue<TerrainChunk>();

    void Start()
    {
        if (!viewer)
            viewer = this.transform;

        mapGenerator = FindObjectOfType<MapGenerator>();

        chunkSize = MapGenerator.mapChunkSize - 1;

        chunkVisibleInViewDst =
            Mathf.RoundToInt(
                mapGenerator.terData.maxViewDst / chunkSize);

        // Regenerate();
    }

    void Update()
    {
        while (foliageSpawnQueue.Count > 0)
        {
            TerrainChunk chunk =
                foliageSpawnQueue.Dequeue();

            chunk.SpawnFoliageMainThread();
        }
    }

    public void Regenerate()
    {
        mapGenerator.ClearAndReset();

        foliageSpawnQueue.Clear();

        foreach (var chunk in terrainChunkDictionary.Values)
        {
            chunk.Destroy();
        }

        terrainChunkDictionary.Clear();
        terrainChunksVisibleLastUpdate.Clear();

        chunkVisibleInViewDst =
            Mathf.RoundToInt(
                mapGenerator.terData.maxViewDst / chunkSize);

        UpdateVisibleChunks();
    }

    void UpdateVisibleChunks()
    {
        for (int i = 0; i < terrainChunksVisibleLastUpdate.Count; i++)
        {
            terrainChunksVisibleLastUpdate[i].SetVisible(false);
        }

        terrainChunksVisibleLastUpdate.Clear();

        int currentChunkCoordX =
            Mathf.RoundToInt(viewerPosition.x / chunkSize);

        int currentChunkCoordY =
            Mathf.RoundToInt(viewerPosition.y / chunkSize);

        for (int yOffset = -chunkVisibleInViewDst;
             yOffset <= chunkVisibleInViewDst;
             yOffset++)
        {
            for (int xOffset = -chunkVisibleInViewDst;
                 xOffset <= chunkVisibleInViewDst;
                 xOffset++)
            {
                Vector2 viewedChunkCoord =
                    new Vector2(
                        currentChunkCoordX + xOffset,
                        currentChunkCoordY + yOffset);

                if (terrainChunkDictionary.ContainsKey(viewedChunkCoord))
                {
                    terrainChunkDictionary[viewedChunkCoord]
                        .UpdateTerrainChunk();
                }
                else
                {
                    terrainChunkDictionary.Add(
                        viewedChunkCoord,
                        new TerrainChunk(
                            viewedChunkCoord,
                            chunkSize,
                            transform,
                            mapMaterial,
                            foliageData));
                }
            }
        }
    }

    public class TerrainChunk
    {
        GameObject meshObject;

        Vector2 coord;
        Vector2 position;

        Bounds bounds;

        MapData mapData;

        MeshRenderer meshRenderer;
        MeshFilter meshFilter;
        MeshCollider meshCollider;

        FoliageData foliageData;

        GameObject foliageRoot;

        bool foliageSpawned = false;
        bool meshReady = false;

        public TerrainChunk(
            Vector2 coord,
            int size,
            Transform parent,
            Material material,
            FoliageData foliageData)
        {
            this.coord = coord;
            this.foliageData = foliageData;

            position = coord * size;

            bounds = new Bounds(position, Vector2.one * size);

            Vector3 positionV3 =
                new Vector3(position.x, 0, position.y);

            meshObject = new GameObject("TerrainChunk");

            // ВАЖНО
            meshObject.layer =
                LayerMask.NameToLayer("Terrain");

            meshRenderer =
                meshObject.AddComponent<MeshRenderer>();

            meshFilter =
                meshObject.AddComponent<MeshFilter>();

            meshCollider =
                meshObject.AddComponent<MeshCollider>();

            meshRenderer.material = material;

            meshObject.transform.position =
                positionV3 *
                mapGenerator.terData.uniformScale;

            meshObject.transform.parent = parent;

            meshObject.transform.localScale =
                Vector3.one *
                mapGenerator.terData.uniformScale;

            SetVisible(false);

            mapGenerator.RequestMapData(
                position,
                OnMapDataReceived);
        }

        void OnMapDataReceived(MapData mapData)
        {
            this.mapData = mapData;

            mapGenerator.RequestMeshData(
                mapData,
                OnMeshDataReceived);

            UpdateTerrainChunk();
        }

        void OnMeshDataReceived(MeshData meshData)
        {
            meshFilter.mesh = meshData.CreateMesh();

            meshCollider.sharedMesh =
                meshFilter.mesh;

            meshReady = true;

            foliageSpawnQueue.Enqueue(this);
        }

        public void SpawnFoliageMainThread()
        {
            if (foliageSpawned)
                return;

            if (!meshReady)
                return;

            if (foliageData == null)
            {
                Debug.LogWarning(
                    "[FoliageSpawner] foliageData == null!");

                return;
            }

            foliageSpawned = true;

            Vector3 worldCenter =
                meshObject.transform.position;

            float worldSize =
                (MapGenerator.mapChunkSize - 1) *
                mapGenerator.terData.uniformScale;

            foliageRoot = FoliageSpawner.Spawn(
                chunkCoord: coord,
                chunkWorldCenter: worldCenter,
                chunkWorldSize: worldSize,
                heightMap: mapData.height_map,
                foliageData: foliageData,
                uniformScale:
                    mapGenerator.terData.uniformScale,
                meshHeightMultiplier:
                    mapGenerator.terData.meshHeightMultiplayer,
                parent:
                    meshObject.transform.parent
            );

            if (foliageRoot != null)
            {
                foliageRoot.SetActive(
                    meshObject.activeSelf);
            }
        }

        public void UpdateTerrainChunk()
        {
            float viewerDstFromNearestEdge =
                Mathf.Sqrt(
                    bounds.SqrDistance(viewerPosition));

            bool visible =
                viewerDstFromNearestEdge <=
                mapGenerator.terData.maxViewDst;

            terrainChunksVisibleLastUpdate.Add(this);

            SetVisible(visible);
        }

        public void SetVisible(bool visible)
        {
            meshObject.SetActive(visible);

            if (foliageRoot != null)
                foliageRoot.SetActive(visible);
        }

        public bool IsVisible()
        {
            return meshObject.activeSelf;
        }

        public void Destroy()
        {
            GameObject.Destroy(meshObject);

            if (foliageRoot != null)
                GameObject.Destroy(foliageRoot);
        }
    }
}