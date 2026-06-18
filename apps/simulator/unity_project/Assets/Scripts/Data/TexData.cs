using UnityEngine;
using System.Collections;
using System.Linq;

[CreateAssetMenu()]
public class TexData : ScriptableObject
{
    const int textureSize = 1024;
    const TextureFormat textureFormat = TextureFormat.RGB565;

    public Layer[] layers;

    public void UpdateMeshHeights(Material material, float minHeight, float maxHeight)
    {
        if (material != null)
        {
            material.SetFloat("_MinHeight", minHeight);
            material.SetFloat("_MaxHeight", maxHeight);
            
            material.SetInt("_LayersCount", layers.Length);
            
            Vector4[] colors = new Vector4[layers.Length];
            Texture2D[] textures = new Texture2D[layers.Length];
            float[] startHeights = new float[layers.Length];
            float[] blends = new float[layers.Length];
            float[] strengths = new float[layers.Length];
            float[] scales = new float[layers.Length];
            
            for (int i = 0; i < layers.Length; i++)
            {
                textures[i] = layers[i].texture;
                colors[i] = layers[i].tint;
                startHeights[i] = layers[i].startHeight;
                blends[i] = layers[i].blendStrength;
                strengths[i] = layers[i].tintStrength;
                scales[i] = layers[i].textureScale;
            }
            
            material.SetVectorArray("_BaseColors", colors);
            material.SetFloatArray("_BaseStartHeights", startHeights);
            material.SetFloatArray("_BaseBlends", blends);
            material.SetFloatArray("_BaseColorStrengths", strengths);
            material.SetFloatArray("_BaseTextureScales", scales);

            Texture2DArray texturesArray = GenerateTextureArray(textures);
            material.SetTexture("_BaseTextures", texturesArray);
        }
    }

    Texture2DArray GenerateTextureArray(Texture2D[] textures)
    {
        // Проверяем, что все текстуры существуют
        for (int i = 0; i < textures.Length; i++)
        {
            if (textures[i] == null)
            {
                Debug.LogError($"Texture at index {i} is null!");
                return null;
            }
        }

        Texture2DArray textureArray = new Texture2DArray(textureSize, textureSize, textures.Length, textureFormat, true);
        
        for (int i = 0; i < textures.Length; i++)
        {
            // Изменяем размер текстуры до нужного
            Texture2D resizedTexture = ResizeTexture(textures[i], textureSize, textureSize);
            
            // Получаем пиксели и устанавливаем их в Texture2DArray
            Color[] pixels = resizedTexture.GetPixels();
            
            // Проверяем размер массива
            if (pixels.Length != textureSize * textureSize)
            {
                Debug.LogError($"Texture {textures[i].name} has wrong size! Expected {textureSize * textureSize}, got {pixels.Length}");
                continue;
            }
            
            textureArray.SetPixels(pixels, i);
        }
        
        textureArray.Apply();
        return textureArray;
    }

    Texture2D ResizeTexture(Texture2D source, int targetWidth, int targetHeight)
    {
        RenderTexture rt = RenderTexture.GetTemporary(targetWidth, targetHeight);
        rt.filterMode = FilterMode.Bilinear;
        
        RenderTexture.active = rt;
        Graphics.Blit(source, rt);
        
        Texture2D result = new Texture2D(targetWidth, targetHeight, source.format, false);
        result.ReadPixels(new Rect(0, 0, targetWidth, targetHeight), 0, 0);
        result.Apply();
        
        RenderTexture.active = null;
        RenderTexture.ReleaseTemporary(rt);
        
        return result;
    }

    [System.Serializable]
    public class Layer
    {
        public Texture2D texture;
        public Color tint;
        [Range(0, 1)]
        public float tintStrength;
        [Range(0, 1)]
        public float startHeight;
        [Range(0, 1)]
        public float blendStrength;
        public float textureScale;
    }
}