using UnityEngine;
public class GoalDetector : MonoBehaviour
{
    public string robotTag = "robotCollider";
    private EventPublisher eventPublisher;
    void Start()
    {
        eventPublisher = FindObjectOfType<EventPublisher>();
    }
    void OnTriggerEnter(Collider other)
    {
        if (!other.CompareTag(robotTag)) return;
        if (eventPublisher == null) return;

        RobotIdentity identity = other.transform.root.GetComponentInChildren<RobotIdentity>();
        int robotId = identity != null ? identity.ID : 0;
        eventPublisher.PublishEvent(0, transform.position, robotId); // 0 = GOAL
    }
}