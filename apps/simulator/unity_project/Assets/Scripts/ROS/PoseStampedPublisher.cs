using System.Collections;
using System.Collections.Generic;
using UnityEngine;

using Unity.Robotics.Core;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using RosMessageTypes.Std;
using RosMessageTypes.Geometry;

/// <summary>
///     This script publishes robot stamped pose
/// </summary>
public class PoseStampedPublisher : MonoBehaviour
{
    // ROS Connector
    private ROSConnection ros;
    // Variables required for ROS communication
    public string poseStampedTopicName = "pose";
    public bool useRobotID = true;
    
    // Transform
    public Transform publishedTransform;

    // Message
    private PoseStampedMsg poseStamped;
    private string frameID = "pose";
    public float publishRate = 10f;

    private RobotIdentity robotIdentity;
    private string fullTopicName;

    void Start()
    {
        robotIdentity = GetComponent<RobotIdentity>();
        fullTopicName = BuildTopicName(poseStampedTopicName);

        // Get ROS connection static instance
        ros = ROSConnection.GetOrCreateInstance();
        ros.RegisterPublisher<PoseStampedMsg>(fullTopicName);

        // Initialize message
        poseStamped = new PoseStampedMsg
        {
            header = new HeaderMsg(
                new TimeStamp(Clock.time), frameID
            )
        };

        InvokeRepeating("PublishPoseStamped", 1f, 1f/publishRate);
    }

    private string BuildTopicName(string baseTopic)
    {
        string result = baseTopic;
        if (result.StartsWith("/")) result = result.TrimStart('/');
        if (useRobotID && robotIdentity != null)
            result = robotIdentity.GetTopic(result);
        if (!result.StartsWith("/")) result = "/" + result;
        
        return result;
    }

    private void PublishPoseStamped()
    {
        poseStamped.header = new HeaderMsg(
            new TimeStamp(Clock.time), frameID
        );

        poseStamped.pose.position = publishedTransform.position.To<FLU>();
        poseStamped.pose.orientation = publishedTransform.rotation.To<FLU>();

        ros.Publish(fullTopicName, poseStamped);
    }

    void OnDestroy()
    {
        CancelInvoke("PublishPoseStamped");
    }
}
