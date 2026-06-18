using UnityEngine;
using RosMessageTypes.Forest;

public abstract class EnvSetGoalBase : RosService<SetGoalRequest, SetGoalResponse> { }

public class EnvSetGoal : EnvSetGoalBase
{
    [Header("Goal Settings")]
    public GameObject goalPrefab;
    public string goalTag = "goal";

    protected override void OnStart() { }

    protected override SetGoalResponse HandleReset(SetGoalRequest request)
    {
        try
        {
            // Удаляем старую цель
            GameObject[] existing = GameObject.FindGameObjectsWithTag(goalTag);
            foreach (var obj in existing)
                Destroy(obj);

            // Спавним новую
            Vector3 pos = new Vector3(request.position_x, request.position_y, request.position_z);
            GameObject goal = Instantiate(goalPrefab, pos, Quaternion.identity);
            goal.tag = goalTag;

            // Меняем размер SphereCollider
            SphereCollider col = goal.GetComponent<SphereCollider>();
            if (col != null)
                col.radius = request.radius;

            // Меняем визуальный размер
            goal.transform.localScale = Vector3.one * request.radius;

            return new SetGoalResponse { success = true, message = "Goal set" };
        }
        catch (System.Exception e)
        {
            return new SetGoalResponse { success = false, message = e.Message };
        }
    }
}