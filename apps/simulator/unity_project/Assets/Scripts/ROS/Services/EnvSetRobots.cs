using UnityEngine;
using RosMessageTypes.Forest;

public abstract class EnvSetRobotsBase : RosService<SetRobotsRequest, SetRobotsResponse> { }

public class EnvSetRobots : EnvSetRobotsBase
{
    private EnvReset envReset;

    [Header("Spawn Point Prefab")]
    public GameObject spawnPointPrefab;

    protected override void OnStart()
    {
        envReset = GetComponent<EnvReset>();
    }

    protected override SetRobotsResponse HandleReset(SetRobotsRequest request)
    {
        try
        {
            int count = request.positions_x.Length;

            if (request.positions_y.Length != count ||
                request.positions_z.Length != count ||
                request.type.Length != count)
            {
                return new SetRobotsResponse
                {
                    success = false,
                    message = "Array lengths mismatch"
                };
            }

            foreach (var info in envReset.spawnInfos)
            {
                if (info.point != null)
                    Destroy(info.point.gameObject);
            }
            envReset.spawnInfos.Clear();

            for (int i = 0; i < count; i++)
            {
                Vector3 pos = new Vector3(
                    request.positions_x[i],
                    request.positions_y[i],
                    request.positions_z[i]
                );

                float rotY = i < request.rotations_y.Length
                    ? request.rotations_y[i]
                    : 0f;

                GameObject spawnPoint = new GameObject($"SpawnPoint_{i}");
                spawnPoint.transform.position = pos;
                spawnPoint.transform.rotation = Quaternion.Euler(0, rotY, 0);

                if (spawnPointPrefab != null)
                {
                    GameObject prefabInstance = Instantiate(spawnPointPrefab, spawnPoint.transform);

                    prefabInstance.transform.localPosition = Vector3.zero;
                    prefabInstance.transform.localRotation = Quaternion.identity;
                }

                envReset.spawnInfos.Add(new EnvReset.SpawnInfo
                {
                    point = spawnPoint.transform,
                    robotType = request.type[i]
                });
            }

            return new SetRobotsResponse
            {
                success = true,
                message = $"Set {count} spawn points"
            };
        }
        catch (System.Exception e)
        {
            return new SetRobotsResponse
            {
                success = false,
                message = e.Message
            };
        }
    }
}