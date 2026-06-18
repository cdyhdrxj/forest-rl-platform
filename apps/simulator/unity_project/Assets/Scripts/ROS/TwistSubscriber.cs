using System.Collections;
using System.Collections.Generic;
using UnityEngine;

using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.ROSGeometry;
using RosMessageTypes.Geometry;

/// <summary>
///     This script subscribes to twist command
///     and use robot controller to 
/// </summary>
public class TwistSubscriber : MonoBehaviour
{
    // ROS Connector
    private ROSConnection ros;
    // Variables required for ROS communication
    public string twistTopicName = "cmd_vel";
    public bool useRobotID = true;

    public ArticulationWheelController wheelController;
    private float targetLinearSpeed;
    private float targetAngularSpeed;
    
    private RobotIdentity robotIdentity;
    private string fullTopicName;

    void Start()
    {
        robotIdentity = GetComponent<RobotIdentity>();
        fullTopicName = BuildTopicName(twistTopicName);

        // Get ROS connection static instance
        ros = ROSConnection.GetOrCreateInstance();

        targetLinearSpeed = 0f;
        targetAngularSpeed = 0f;
        
        ros.Subscribe<TwistMsg>(fullTopicName, UpdateVelocity);
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

    void FixedUpdate()
    {
        wheelController.SetRobotVelocity(targetLinearSpeed, targetAngularSpeed);
    }

    private void UpdateVelocity(TwistMsg twist)
    {
        targetLinearSpeed = twist.linear.From<FLU>().z;
        targetAngularSpeed = twist.angular.From<FLU>().y;
    }
}
