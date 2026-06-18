using UnityEngine;
using System.Collections;

public class MapDisplay : MonoBehaviour
{
    public Renderer texture_renderer;
    public MeshFilter meshFilter;
    public MeshRenderer meshRenderer;

    public void DrawTexture(Texture2D texture) 
    {
        texture_renderer.sharedMaterial.mainTexture = texture;
        // texture_renderer.transform.localScale = new Vector3(texture.width, 1, texture.height);
    }

    public void DrawMesh(MeshData meshData)
    {
        meshFilter.sharedMesh = meshData.CreateMesh();
    }
}
