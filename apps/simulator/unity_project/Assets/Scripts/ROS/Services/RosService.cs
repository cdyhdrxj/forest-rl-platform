using System.Collections.Generic;
using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using Unity.Robotics.ROSTCPConnector.MessageGeneration;
using RosMessageTypes.Std;

public abstract class RosService : MonoBehaviour
{
    [Header("ROS Settings")]
    public string serviceName = "/env/none";
    
    protected ROSConnection ros;

    void Start()
    {
        Debug.Log($"RosService Start: {serviceName}");
        ros = ROSConnection.GetOrCreateInstance();
        ros.ImplementService<TriggerRequest, TriggerResponse>(serviceName, HandleReset);
        
        OnStart();
    }

    protected virtual void OnStart()
    {
        
    }

    protected abstract TriggerResponse HandleReset(TriggerRequest request);
}

public abstract class RosService<TRequest, TResponse> : MonoBehaviour
    where TRequest : Message, new()
    where TResponse : Message, new()
{
    [Header("ROS Settings")]
    public string serviceName = "/env/none";

    protected ROSConnection ros;

    void Start()
    {
        Debug.Log($"RosService Start: {serviceName}");
        ros = ROSConnection.GetOrCreateInstance();
        ros.ImplementService<TRequest, TResponse>(serviceName, HandleReset);
        OnStart();
    }

    protected virtual void OnStart() { }

    protected abstract TResponse HandleReset(TRequest request);
}