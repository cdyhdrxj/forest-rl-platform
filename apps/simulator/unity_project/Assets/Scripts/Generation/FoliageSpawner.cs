using UnityEngine;

public static class FoliageSpawner
{
    public static GameObject Spawn(
        Vector2 chunkCoord,
        Vector3 chunkWorldCenter,
        float chunkWorldSize,
        float[,] heightMap,
        FoliageData foliageData,
        float uniformScale,
        float meshHeightMultiplier,
        Transform parent)
    {
        if (foliageData == null || foliageData.layers == null || foliageData.layers.Length == 0)
            return null;

        GameObject root = new GameObject($"Foliage_{chunkCoord.x}_{chunkCoord.y}");
        root.transform.parent   = parent;
        root.transform.position = Vector3.zero;

        int hmFull = heightMap.GetLength(0);
        int meshPx = hmFull - 2;
        int spawnedTotal = 0;

        int terrainMask = LayerMask.GetMask("Terrain");

        foreach (var layer in foliageData.layers)
        {
            if (layer.prefabs == null || layer.prefabs.Length == 0) continue;
            if (layer.density <= 0f) continue;

            int layerSeed = foliageData.seed
                          ^ (int)(chunkCoord.x * 73856093)
                          ^ (int)(chunkCoord.y * 19349663)
                          ^ layer.name.GetHashCode();

            System.Random rng = new System.Random(layerSeed);

            for (int py = 2; py < hmFull - 2; py++)
            {
                for (int px = 2; px < hmFull - 2; px++)
                {
                    if (rng.NextDouble() > layer.density / 10000f)
                        continue;

                    float normalizedHeight = heightMap[px, py];

                    if (normalizedHeight < layer.minHeightThreshold ||
                        normalizedHeight > layer.maxHeightThreshold)
                        continue;

                    float slopeAngle = GetSlopeAngle(heightMap, px, py, hmFull, hmFull);
                    if (slopeAngle < layer.minSlopeAngle || slopeAngle > layer.maxSlopeAngle)
                        continue;

                    float jitterX = ((float)rng.NextDouble() - 0.5f) * 0.35f;
                    float jitterZ = ((float)rng.NextDouble() - 0.5f) * 0.35f;

                    float tX = ((px - 1) + jitterX) / (meshPx - 1f);
                    float tZ = ((py - 1) + jitterZ) / (meshPx - 1f);

                    float worldX = chunkWorldCenter.x + (tX - 0.5f) * chunkWorldSize;
                    float worldZ = chunkWorldCenter.z + (tZ - 0.5f) * chunkWorldSize;

                    Vector3    spawnPos;
                    Quaternion surfaceRotation;

                    if (Physics.Raycast(new Vector3(worldX, 9999f, worldZ), Vector3.down,
                                        out RaycastHit hit, 99999f, terrainMask))
                    {
                        spawnPos = hit.point;

                        // Угол реальной нормали из рейкаста
                        float hitAngle = Vector3.Angle(Vector3.up, hit.normal);

                        if (hitAngle <= layer.maxSlopeAngle)
                        {
                            // Наклон в пределах лимита — используем нормаль как есть
                            surfaceRotation = Quaternion.FromToRotation(Vector3.up, hit.normal);
                        }
                        else
                        {
                            // Наклон слишком большой — зажимаем до maxSlopeAngle
                            // Проецируем нормаль на плоскость XZ чтобы сохранить направление наклона
                            Vector3 tiltAxis = Vector3.Cross(Vector3.up, hit.normal).normalized;
                            surfaceRotation = Quaternion.AngleAxis(layer.maxSlopeAngle, tiltAxis);
                        }
                    }
                    else
                    {
                        spawnPos = new Vector3(worldX,
                            normalizedHeight * meshHeightMultiplier * uniformScale, worldZ);
                        surfaceRotation = Quaternion.identity;
                    }

                    // Случайный поворот по Y поверх ориентации
                    if (layer.randomYRotation)
                        surfaceRotation *= Quaternion.Euler(0f, (float)(rng.NextDouble() * 360f), 0f);

                    GameObject prefab = layer.prefabs[rng.Next(layer.prefabs.Length)];
                    if (prefab == null) continue;

                    GameObject instance = GameObject.Instantiate(
                        prefab, spawnPos, surfaceRotation, root.transform);

                    instance.transform.localScale = Vector3.one *
                        Mathf.Lerp(layer.minScale, layer.maxScale, (float)rng.NextDouble());

                    spawnedTotal++;
                }
            }
        }

        Debug.Log($"[FoliageSpawner] Чанк {chunkCoord}: {spawnedTotal} объектов.");
        return root;
    }

    static float GetSlopeAngle(float[,] hm, int x, int y, int w, int h)
    {
        float hL = hm[Mathf.Max(x - 1, 0),     y];
        float hR = hm[Mathf.Min(x + 1, w - 1), y];
        float hD = hm[x, Mathf.Max(y - 1, 0)];
        float hU = hm[x, Mathf.Min(y + 1, h - 1)];

        return Vector3.Angle(Vector3.up, new Vector3(hL - hR, 2f, hD - hU).normalized);
    }
}
