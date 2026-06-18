#if UNITY_EDITOR && UNITY_INCLUDE_TESTS
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using RosMessageTypes.Forest;
using RosMessageTypes.Std;

/// <summary>
/// Play Mode тесты для сервисов управления средой и системы событий.
/// Путь: Assets/Tests/PlayMode/EnvServicesTests.cs
/// Требует: запущенный ros_tcp_endpoint и rosbridge
/// </summary>
public class EnvServicesTests
{
    private GameObject envResetObj;
    private GameObject envSetRobotsObj;
    private GameObject envSetGoalObj;
    private GameObject eventPublisherObj;
    private EnvReset envReset;
    private EnvSetRobots envSetRobots;
    private EventPublisher eventPublisher;

    [SetUp]
    public void SetUp()
    {
        RobotIDManager.Reset();

        // EnvReset
        envResetObj = new GameObject("EnvReset");
        envReset = envResetObj.AddComponent<EnvReset>();
        envReset.robotTag = "robot";
        envReset.robotPrefabs = new GameObject[0];

        // EnvSetRobots
        envSetRobotsObj = new GameObject("EnvSetRobots");
        envSetRobots = envSetRobotsObj.AddComponent<EnvSetRobots>();

        // EventPublisher
        eventPublisherObj = new GameObject("EventPublisher");
        eventPublisher = eventPublisherObj.AddComponent<EventPublisher>();
        eventPublisher.eventsTopic = "/env/events";

        // EnvSetGoal
        envSetGoalObj = new GameObject("EnvSetGoal");
    }

    [TearDown]
    public void TearDown()
    {
        Object.DestroyImmediate(envResetObj);
        Object.DestroyImmediate(envSetRobotsObj);
        Object.DestroyImmediate(envSetGoalObj);
        Object.DestroyImmediate(eventPublisherObj);
        RobotIDManager.Reset();
    }

    // ===== EnvSetRobots: валидация запросов =====

    [Test]
    public void EnvSetRobots_MismatchArrayLengths_ReturnsFailure()
    {
        var request = new SetRobotsRequest
        {
            positions_x = new float[] { 0f, 1f },
            positions_y = new float[] { 0f },      // длина не совпадает
            positions_z = new float[] { 0f, 1f },
            type        = new int[]   { 0, 0 },
            rotations_y = new float[] { 0f, 0f }
        };

        // Вызываем HandleReset через рефлексию (метод protected)
        var method = typeof(EnvSetRobots).GetMethod(
            "HandleReset",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);

        var response = (SetRobotsResponse)method.Invoke(envSetRobots, new object[] { request });

        Assert.IsFalse(response.success);
        Assert.AreEqual("Array lengths mismatch", response.message);
    }

    [Test]
    public void EnvSetRobots_ValidRequest_ReturnsSuccess()
    {
        // Нужен envReset на том же объекте
        var combinedObj = new GameObject("Combined");
        var reset = combinedObj.AddComponent<EnvReset>();
        reset.robotTag = "robot";
        reset.robotPrefabs = new GameObject[0];
        var setRobots = combinedObj.AddComponent<EnvSetRobots>();

        // Связываем через рефлексию
        var field = typeof(EnvSetRobots).GetField(
            "envReset",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);
        field.SetValue(setRobots, reset);

        var request = new SetRobotsRequest
        {
            positions_x = new float[] { 0f },
            positions_y = new float[] { 0f },
            positions_z = new float[] { 0f },
            type        = new int[]   { 0 },
            rotations_y = new float[] { 0f }
        };

        var method = typeof(EnvSetRobots).GetMethod(
            "HandleReset",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);

        var response = (SetRobotsResponse)method.Invoke(setRobots, new object[] { request });

        Assert.IsTrue(response.success);
        Assert.AreEqual(1, reset.spawnInfos.Count);
        Assert.AreEqual("Set 1 spawn points", response.message);

        Object.DestroyImmediate(combinedObj);
    }

    [Test]
    public void EnvSetRobots_SpawnPoint_CorrectPosition()
    {
        var combinedObj = new GameObject("Combined2");
        var reset = combinedObj.AddComponent<EnvReset>();
        reset.robotTag = "robot";
        reset.robotPrefabs = new GameObject[0];
        var setRobots = combinedObj.AddComponent<EnvSetRobots>();

        var field = typeof(EnvSetRobots).GetField(
            "envReset",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);
        field.SetValue(setRobots, reset);

        var request = new SetRobotsRequest
        {
            positions_x = new float[] { 5f },
            positions_y = new float[] { 0f },
            positions_z = new float[] { 10f },
            type        = new int[]   { 0 },
            rotations_y = new float[] { 90f }
        };

        var method = typeof(EnvSetRobots).GetMethod(
            "HandleReset",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);

        method.Invoke(setRobots, new object[] { request });

        Vector3 spawnPos = reset.spawnInfos[0].point.position;
        Assert.AreEqual(5f,  spawnPos.x, 0.001f);
        Assert.AreEqual(0f,  spawnPos.y, 0.001f);
        Assert.AreEqual(10f, spawnPos.z, 0.001f);

        Object.DestroyImmediate(combinedObj);
    }

    [Test]
    public void EnvSetRobots_EmptyRequest_ReturnsSuccess()
    {
        var combinedObj = new GameObject("Combined3");
        var reset = combinedObj.AddComponent<EnvReset>();
        reset.robotTag = "robot";
        reset.robotPrefabs = new GameObject[0];
        var setRobots = combinedObj.AddComponent<EnvSetRobots>();

        var field = typeof(EnvSetRobots).GetField(
            "envReset",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);
        field.SetValue(setRobots, reset);

        var request = new SetRobotsRequest
        {
            positions_x = new float[0],
            positions_y = new float[0],
            positions_z = new float[0],
            type        = new int[0],
            rotations_y = new float[0]
        };

        var method = typeof(EnvSetRobots).GetMethod(
            "HandleReset",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);

        var response = (SetRobotsResponse)method.Invoke(setRobots, new object[] { request });

        Assert.IsTrue(response.success);
        Assert.AreEqual(0, reset.spawnInfos.Count);

        Object.DestroyImmediate(combinedObj);
    }

    // ===== EnvGenerate: применение параметров =====

    [Test]
    public void EnvGenerate_ApplyNoiseData_SetsCorrectSeed()
    {
        var obj = new GameObject("EnvGenerate");
        var gen = obj.AddComponent<EnvGenerate>();

        var mapGenObj = new GameObject("MapGenerator");
        var mapGen = mapGenObj.AddComponent<MapGenerator>();
        mapGen.noiseData = ScriptableObject.CreateInstance<NoiseData>();
        mapGen.terData   = ScriptableObject.CreateInstance<TerData>();

        // Устанавливаем mapGenerator через рефлексию
        var field = typeof(EnvGenerate).GetField(
            "mapGenerator",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);
        field.SetValue(gen, mapGen);

        var method = typeof(EnvGenerate).GetMethod(
            "ApplyNoiseData",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);

        var request = new SetTerrainParamsRequest
        {
            seed            = 99,
            noise_scale     = 150f,
            octaves         = 4,
            persistance     = 0.5f,
            lacunarity      = 2f,
            offset_x        = 0f,
            offset_y        = 0f,
            noise_normalize_mode = 1
        };

        method.Invoke(gen, new object[] { request });

        Assert.AreEqual(99,    mapGen.noiseData.seed);
        Assert.AreEqual(150f,  mapGen.noiseData.noise_scale, 0.001f);

        Object.DestroyImmediate(obj);
        Object.DestroyImmediate(mapGenObj);
    }

    [Test]
    public void EnvGenerate_ApplyFoliageData_ClampsDensity()
    {
        var obj = new GameObject("EnvGenerate2");
        var gen = obj.AddComponent<EnvGenerate>();

        var foliageData = ScriptableObject.CreateInstance<FoliageData>();
        foliageData.layers = new FoliageData.FoliageLayer[]
        {
            new FoliageData.FoliageLayer { density = 50 }
        };

        var field = typeof(EnvGenerate).GetField(
            "foliageData",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);
        field.SetValue(gen, foliageData);

        var method = typeof(EnvGenerate).GetMethod(
            "ApplyFoliageData",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);

        // Плотность больше 100 — должна зажаться до 100
        var request = new SetTerrainParamsRequest { density = 150 };
        method.Invoke(gen, new object[] { request });

        Assert.AreEqual(100, foliageData.layers[0].density);

        Object.DestroyImmediate(obj);
    }

    // ===== RobotCollisionHandler: cooldown =====

    [Test]
    public void RobotCollisionHandler_Cooldown_InitiallyZero()
    {
        var obj = new GameObject("CollisionHandler");
        var handler = obj.AddComponent<RobotCollisionHandler>();

        var field = typeof(RobotCollisionHandler).GetField(
            "lastCollisionTime",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);

        float lastTime = (float)field.GetValue(handler);
        Assert.AreEqual(0f, lastTime, 0.001f);

        Object.DestroyImmediate(obj);
    }

    [Test]
    public void RobotCollisionHandler_Cooldown_IsHalfSecond()
    {
        var obj = new GameObject("CollisionHandler2");
        var handler = obj.AddComponent<RobotCollisionHandler>();

        var field = typeof(RobotCollisionHandler).GetField(
            "collisionCooldown",
            System.Reflection.BindingFlags.NonPublic |
            System.Reflection.BindingFlags.Instance);

        float cooldown = (float)field.GetValue(handler);
        Assert.AreEqual(0.5f, cooldown, 0.001f);

        Object.DestroyImmediate(obj);
    }

    // ===== EventPublisher: формирование сообщения =====

    [Test]
    public void EventPublisher_TopicName_IsCorrect()
    {
        Assert.AreEqual("/env/events", eventPublisher.eventsTopic);
    }

    [Test]
    public void EventPublisher_CustomTopic_IsSet()
    {
        var obj = new GameObject("EventPublisher2");
        var pub = obj.AddComponent<EventPublisher>();
        pub.eventsTopic = "/custom/events";

        Assert.AreEqual("/custom/events", pub.eventsTopic);

        Object.DestroyImmediate(obj);
    }
}
#endif