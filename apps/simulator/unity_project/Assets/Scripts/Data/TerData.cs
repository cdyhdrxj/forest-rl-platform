using UnityEngine;
using System.Collections;

[CreateAssetMenu()]
public class TerData : ScriptableObject
{
    public float uniformScale = .1f;
    public float meshHeightMultiplayer;
    public AnimationCurve meshHeightCurve;

    public int maxViewDst = 300;

    public float minHeight
    {
        get
        {
            return uniformScale * meshHeightMultiplayer * meshHeightCurve.Evaluate(0);
        }
    }

    public float maxHeight
    {
        get
        {
            return uniformScale * meshHeightMultiplayer * meshHeightCurve.Evaluate(1);
        }
    }
}
