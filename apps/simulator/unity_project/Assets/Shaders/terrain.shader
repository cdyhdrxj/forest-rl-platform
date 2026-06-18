Shader "Custom/terrain"
{
    Properties
    {
        _TestTexture("Texture", 2D) = "white"{}
        _TestScale("Scale", Float) = 1
        _MinHeight("Min Height", Float) = 0
        _MaxHeight("Max Height", Float) = 1
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" }
        LOD 200

        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows
        #pragma target 3.0

        const static int maxLayerCount = 8;
        const static float epsilon = 1E-4;

        float _MinHeight;
        float _MaxHeight;
        
        sampler2D _TestTexture;
        float _TestScale;

        int _LayersCount;
        float4 _BaseColors[maxLayerCount];
        float _BaseStartHeights[maxLayerCount];
        float _BaseBlends[maxLayerCount];
        float _BaseColorStrengths[maxLayerCount];
        float _BaseTextureScales[maxLayerCount];

        UNITY_DECLARE_TEX2DARRAY(_BaseTextures);

        struct Input
        {
            float3 worldPos;
            float3 worldNormal;
        };

        float inverseLerp(float a, float b, float value)
        {
            return saturate((value - a) / (b - a));
        }

        float3 triplanar(float3 worldPos, float scale, float3 blendAxes, int textureIndex) {
            float3 scaledWorldPos = worldPos / _TestScale;

            float3 xProjection = UNITY_SAMPLE_TEX2DARRAY(_BaseTextures, float3(scaledWorldPos.y, scaledWorldPos.z, textureIndex)) * blendAxes.x;
            float3 yProjection = UNITY_SAMPLE_TEX2DARRAY(_BaseTextures, float3(scaledWorldPos.x, scaledWorldPos.z, textureIndex)) * blendAxes.y;
            float3 zProjection = UNITY_SAMPLE_TEX2DARRAY(_BaseTextures, float3(scaledWorldPos.x, scaledWorldPos.y, textureIndex)) * blendAxes.z;

            return xProjection + yProjection + zProjection;
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            float heightPercent = inverseLerp(_MinHeight, _MaxHeight, IN.worldPos.y);
            float3 blendAxes = abs(IN.worldNormal);
            blendAxes /= blendAxes.x + blendAxes.y + blendAxes.z;            

            float3 albedo = float3(0, 0, 0);
            
            for (int i = 0; i < _LayersCount; i++)
            {
                float drawStrength = inverseLerp(
                    -_BaseBlends[i] / 2 - epsilon, 
                    _BaseBlends[i] / 2, 
                    heightPercent - _BaseStartHeights[i]
                );

                float3 baseColor = _BaseColors[i] * _BaseColorStrengths[i];
                float3 textureColor = triplanar(IN.worldPos, _BaseTextureScales[i], blendAxes, i) * (1 - _BaseColorStrengths[i]);

                albedo = albedo * (1 - drawStrength) + (baseColor + textureColor) * drawStrength;
            }
            
            o.Albedo = albedo;
        }
        ENDCG
    }
    FallBack "Diffuse"
}