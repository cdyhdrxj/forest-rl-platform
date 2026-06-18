using UnityEngine;
using RosMessageTypes.Std;
using RosMessageTypes.BuiltinInterfaces;
using RosMessageTypes.Forest;
using Unity.Robotics.ROSTCPConnector;

public class EventPublisher : MonoBehaviour
{
    [Header("ROS Settings")]
    public string eventsTopic = "/env/events";

    private ROSConnection ros;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<EventMsg>(eventsTopic);
    }

    public void PublishEvent(int type, Vector3 position, int robotId = 0)
    {
        var msg = new EventMsg
        {
            header = new HeaderMsg
            {
                stamp = new TimeMsg
                {
                    sec = (int)Time.time,
                    nanosec = (uint)((Time.time - (int)Time.time) * 1e9)
                },
                frame_id = ""
            },
            type = (byte)type,
            robot_id = (byte)robotId,
            x = position.x,
            y = position.z,
            value = 0f
        };

        ros.Publish(eventsTopic, msg);
        Debug.Log($"Событие {type} робот {robotId} опубликовано");
    }
}