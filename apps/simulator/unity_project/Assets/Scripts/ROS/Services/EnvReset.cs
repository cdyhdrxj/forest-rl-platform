using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using RosMessageTypes.Std;

public class EnvReset : RosService
{
    [Header("Robot Settings")]
    public string robotTag = "robot";

    [Header("Robot Prefabs by Type")]
    public GameObject[] robotPrefabs;

    public struct SpawnInfo
    {
        public Transform point;
        public int robotType;
    }

    public List<SpawnInfo> spawnInfos = new List<SpawnInfo>();
    private List<GameObject> spawnedRobots = new List<GameObject>();

    protected override void OnStart() { }

    private void SpawnAllRobots()
    {
        foreach (var info in spawnInfos)
        {
            if (info.robotType < 0 || info.robotType >= robotPrefabs.Length) continue;
            GameObject prefab = robotPrefabs[info.robotType];
            if (!prefab) continue;

            GameObject robot = Instantiate(prefab, info.point.position, info.point.rotation);
            robot.tag = robotTag;
            spawnedRobots.Add(robot);
            Debug.Log($"Создан робот типа {info.robotType} в {info.point.position}");
        }
    }

    private void DestroyAllRobots()
    {
        GameObject[] existingRobots = GameObject.FindGameObjectsWithTag(robotTag);
        foreach (GameObject robot in existingRobots)
            Destroy(robot);

        spawnedRobots.Clear();
        RobotIDManager.Reset();
        Debug.Log($"Удалено роботов: {existingRobots.Length}");
    }

    private IEnumerator ResetCoroutine()
    {
        DestroyAllRobots();
        yield return null; // ждём конец кадра пока Destroy отработает
        SpawnAllRobots();
    }

    protected override TriggerResponse HandleReset(TriggerRequest request)
    {
        Debug.Log("Вызван сервис /env/reset");

        try
        {
            StartCoroutine(ResetCoroutine());
        }
        catch (System.Exception e)
        {
            Debug.LogError("Env reset failed: " + e.Message);
            return new TriggerResponse { success = false, message = e.Message };
        }

        return new TriggerResponse { success = true, message = "Env reset completed" };
    }
}