using UnityEngine;

public class RobotIdentity : MonoBehaviour
{
    public int robotId = -1;
    public bool autoAssignId = true;
    public bool saveToPlayerPrefs = false;
    
    private int cachedID = -1;
    private string cachedPrefix;
    
    public int ID
    {
        get
        {
            if (cachedID == -1)
            {
                if (robotId != -1 && autoAssignId)
                {
                    RobotIDManager.SetRobotID(gameObject, robotId);
                    cachedID = robotId;
                }
                else
                {
                    cachedID = RobotIDManager.GetRobotID(gameObject);
                }
                cachedPrefix = $"/robot_{cachedID}";
            }
            return cachedID;
        }
    }
    
    public string TopicPrefix => cachedPrefix;
    
    void Awake()
    {
        _ = ID;
        
        if (saveToPlayerPrefs)
        {
            RobotIDManager.SaveToPlayerPrefs();
        }
        
        Debug.Log($"Робот '{gameObject.name}' (ID: {ID}) инициализирован");
    }
    
    public string GetTopic(string topicName)
    {
        if (topicName.StartsWith("/")) topicName = topicName.TrimStart('/');
        return $"{TopicPrefix}/{topicName}";
    }
    
    void OnDestroy()
    {
        RobotIDManager.ReleaseID(ID);
    }
}