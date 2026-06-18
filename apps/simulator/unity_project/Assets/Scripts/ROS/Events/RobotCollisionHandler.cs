using UnityEngine;

public class RobotCollisionHandler : MonoBehaviour
{
    private float lastCollisionTime = 0f;
    private float collisionCooldown = 0.5f;
    private EventPublisher eventPublisher;
    [SerializeField]
    private RobotIdentity robotIdentity;

    void Start()
    {
        eventPublisher = FindObjectOfType<EventPublisher>();
    }

    void OnCollisionEnter(Collision collision)
    {
        if (Time.time - lastCollisionTime < collisionCooldown) return;
        lastCollisionTime = Time.time;

        int eventType = collision.gameObject.CompareTag("impassible") ? 3 : 2;
        int robotId = robotIdentity != null ? robotIdentity.ID : 0;

        eventPublisher.PublishEvent(eventType, collision.contacts[0].point, robotId);
    }
}