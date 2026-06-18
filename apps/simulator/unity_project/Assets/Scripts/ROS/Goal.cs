using System;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;

using Unity.Robotics.Core;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using RosMessageTypes.Geometry;
using RosMessageTypes.Std;

public class SimpleGoal : MonoBehaviour
{
    private ROSConnection ros;
    public string goalTopic = "/goal_pose";
    public Transform goalObject;
    public float publishRate = 5f;

    void Start()
    {
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(goalTopic);
        InvokeRepeating("PublishGoal", 1f, 1f/publishRate);
    }

    void PublishGoal()
    {
        if (goalObject == null) return;

        PoseStampedMsg goalMsg = new PoseStampedMsg
        {
            header = new HeaderMsg
            {
                frame_id = "map",
                stamp = new TimeStamp(Clock.time)
            },
            pose = new PoseMsg
            {
                position = goalObject.position.To<FLU>(),
                orientation = Quaternion.identity.To<FLU>()
            }
        };

        ros.Publish(goalTopic, goalMsg);
    }
}