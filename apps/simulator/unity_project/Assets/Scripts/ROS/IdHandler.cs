using UnityEngine;
using System.Collections.Generic;
using System.Linq;

public static class RobotIDManager
{
    private static Dictionary<string, int> robotIDs = new Dictionary<string, int>();
    private static int nextID = 0;
    
    private static bool isReset = false;
    
    public static int GetRobotID(GameObject robot)
    {
        if (robot == null)
        {
            Debug.LogError("RobotIDManager: robot is null!");
            return -1;
        }
        
        string key = GetRobotKey(robot);
        
        if (!robotIDs.ContainsKey(key))
        {
            robotIDs[key] = nextID;
            Debug.Log($"Роботу '{robot.name}' (InstanceID: {key}) назначен ID: {nextID}");
            nextID++;
        }
        
        return robotIDs[key];
    }
    
    public static void SetRobotID(GameObject robot, int id)
    {
        if (robot == null) return;
        
        string key = GetRobotKey(robot);
        
        if (robotIDs.ContainsValue(id) && (!robotIDs.ContainsKey(key) || robotIDs[key] != id))
        {
            Debug.LogWarning($"ID {id} уже используется другим роботом!");
            return;
        }
        
        robotIDs[key] = id;
        Debug.Log($"Роботу '{robot.name}' установлен ID: {id}");
        
        if (id >= nextID)
            nextID = id + 1;
    }
    
    private static string GetRobotKey(GameObject robot)
    {
        string sceneName = UnityEngine.SceneManagement.SceneManager.GetActiveScene().name;
        return $"{sceneName}_{robot.GetInstanceID()}";
    }
    
    public static string GetTopicPrefix(GameObject robot)
    {
        int id = GetRobotID(robot);
        return $"/robot_{id}";
    }
    
    public static string GetFullTopic(GameObject robot, string topicName)
    {
        if (topicName.StartsWith("/")) topicName = topicName.TrimStart('/');
        return $"{GetTopicPrefix(robot)}/{topicName}";
    }
    
    public static Dictionary<string, int> GetAllRobots()
    {
        return new Dictionary<string, int>(robotIDs);
    }
    
    public static void Reset()
    {
        robotIDs.Clear();
        nextID = 0;
        isReset = true;
        Debug.Log("RobotIDManager: Все ID сброшены");
    }
    
    public static void SaveToPlayerPrefs()
    {
        string data = string.Join(",", robotIDs.Select(kv => $"{kv.Key}:{kv.Value}"));
        PlayerPrefs.SetString("RobotIDs", data);
        PlayerPrefs.Save();
        Debug.Log("RobotIDManager: ID сохранены в PlayerPrefs");
    }
    
    public static void LoadFromPlayerPrefs()
    {
        if (PlayerPrefs.HasKey("RobotIDs"))
        {
            string data = PlayerPrefs.GetString("RobotIDs");
            var pairs = data.Split(',');
            foreach (var pair in pairs)
            {
                var parts = pair.Split(':');
                if (parts.Length == 2 && int.TryParse(parts[1], out int id))
                {
                    robotIDs[parts[0]] = id;
                    if (id >= nextID) nextID = id + 1;
                }
            }
            Debug.Log($"RobotIDManager: Загружено {robotIDs.Count} ID из PlayerPrefs");
        }
    }

    public static void ReleaseID(int id)
{
    string keyToRemove = null;
    foreach (var kv in robotIDs)
    {
        if (kv.Value == id)
        {
            keyToRemove = kv.Key;
            break;
        }
    }
    if (keyToRemove != null)
        robotIDs.Remove(keyToRemove);
}
}

#if UNITY_EDITOR
[UnityEditor.InitializeOnLoad]
#endif
public static class RobotIDInitializer
{
    static RobotIDInitializer()
    {
        #if UNITY_EDITOR
        UnityEditor.EditorApplication.playModeStateChanged += (change) =>
        {
            if (change == UnityEditor.PlayModeStateChange.ExitingEditMode)
            {
                RobotIDManager.Reset();
            }
        };
        #endif
    }
    
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    private static void OnBeforeSceneLoad()
    {
        RobotIDManager.Reset();
    }
}