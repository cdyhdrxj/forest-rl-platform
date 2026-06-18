using UnityEngine;
using System.Collections;
using UnityEditor;

// [CustomEditor(typeof(MapGenerator))]
public class MapGeneratorEditor : Editor
{
    public override void OnInspectorGUI()
    {
        // MapGenerator map_gen = (MapGenerator)target;

        // if (DrawDefaultInspector())
        // {
        //     if (map_gen.auto_update)
        //     {
        //         map_gen.DrawMapInEditor();
        //     }
        // }

        // if (GUILayout.Button("Generate"))
        // {
        //     map_gen.DrawMapInEditor();
        // }
    }
}
