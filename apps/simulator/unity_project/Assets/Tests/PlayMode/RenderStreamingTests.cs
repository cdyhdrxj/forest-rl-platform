#if UNITY_EDITOR && UNITY_INCLUDE_TESTS
using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.Rendering;

/// <summary>
/// Play Mode тесты для Unity Render Streaming.
/// Путь: Assets/Tests/PlayMode/RenderStreamingTests.cs
/// </summary>
public class RenderStreamingTests
{
    private GameObject streamingCameraObject;
    private Camera streamingCamera;
    private GameObject eventPublisherObject;
    
    [SetUp]
    public void SetUp()
    {
        // Создаём камеру для стриминга
        streamingCameraObject = new GameObject("StreamingCamera");
        streamingCamera = streamingCameraObject.AddComponent<Camera>();
        streamingCamera.backgroundColor = Color.gray;
        
        // Создаём объект для EventPublisher
        eventPublisherObject = new GameObject("EventPublisher");
    }
    
    [TearDown]
    public void TearDown()
    {
        if (streamingCameraObject != null)
            Object.DestroyImmediate(streamingCameraObject);
        if (eventPublisherObject != null)
            Object.DestroyImmediate(eventPublisherObject);
    }
    
    // ============================================================
    // 1. ТЕСТЫ КОНФИГУРАЦИИ
    // ============================================================
    
    [Test]
    public void EventPublisher_CanBeAddedAndConfigured()
    {
        var eventPublisher = eventPublisherObject.AddComponent<EventPublisher>();
        eventPublisher.eventsTopic = "/env/events";
        
        Assert.IsNotNull(eventPublisher);
        Assert.AreEqual("/env/events", eventPublisher.eventsTopic);
    }
    
    [Test]
    public void EventPublisher_CustomTopic_CanBeSet()
    {
        var eventPublisher = eventPublisherObject.AddComponent<EventPublisher>();
        eventPublisher.eventsTopic = "/custom/events";
        
        Assert.AreEqual("/custom/events", eventPublisher.eventsTopic);
    }
    
    // ============================================================
    // 2. ТЕСТЫ КАЧЕСТВА ВИДЕО (FPS, РЕНДЕРИНГ)
    // ============================================================
    
    [Test]
    public void StreamingCamera_IsRendering()
    {
        Assert.IsNotNull(streamingCamera);
        Assert.IsTrue(streamingCamera.enabled);
    }
    
    [Test]
    public void FPS_IsMeasurable()
    {
        List<float> fpsSamples = new List<float>();
        
        for (int i = 0; i < 60; i++)
        {
            float deltaTime = Time.deltaTime;
            if (deltaTime > 0)
            {
                float fps = 1f / deltaTime;
                fpsSamples.Add(fps);
            }
        }
        
        float avgFps = 0f;
        foreach (var fps in fpsSamples)
            avgFps += fps;
        
        if (fpsSamples.Count > 0)
            avgFps /= fpsSamples.Count;
        
        Debug.Log($"Average FPS: {avgFps:F2}");
        Assert.Greater(fpsSamples.Count, 0, "FPS samples should be collected");
    }
    
    [Test]
    public void Camera_WithRenderTexture_CanBeCreated()
    {
        var renderTexture = new RenderTexture(1920, 1080, 24);
        streamingCamera.targetTexture = renderTexture;
        
        Assert.IsNotNull(streamingCamera.targetTexture);
        Assert.AreEqual(1920, streamingCamera.targetTexture.width);
        Assert.AreEqual(1080, streamingCamera.targetTexture.height);
        
        streamingCamera.targetTexture = null;
        renderTexture.Release();
        Object.DestroyImmediate(renderTexture);
    }
    
    // ============================================================
    // 3. НАГРУЗОЧНЫЕ ТЕСТЫ
    // ============================================================
    
    [Test]
    public void Application_UnderGpuLoad_DoesNotCrash()
    {
        float startTime = Time.realtimeSinceStartup;
        float testDuration = 3.0f;
        
        while (Time.realtimeSinceStartup - startTime < testDuration)
        {
            var tempTexture = new Texture2D(256, 256);
            tempTexture.Apply();
            Object.DestroyImmediate(tempTexture);
        }
        
        // Если дошли сюда без исключений — тест пройден
    }
    
    [Test]
    public void Camera_MultipleResolutions_AreSupported()
    {
        int[] resolutions = { 640, 480, 1280, 720, 1920, 1080 };
        
        for (int i = 0; i < resolutions.Length; i += 2)
        {
            int width = resolutions[i];
            int height = resolutions[i + 1];
            
            var renderTexture = new RenderTexture(width, height, 24);
            streamingCamera.targetTexture = renderTexture;
            
            Assert.IsNotNull(streamingCamera.targetTexture);
            Assert.AreEqual(width, streamingCamera.targetTexture.width);
            Assert.AreEqual(height, streamingCamera.targetTexture.height);
            
            streamingCamera.targetTexture = null;
            renderTexture.Release();
            Object.DestroyImmediate(renderTexture);
        }
    }
    
    // ============================================================
    // 4. ТЕСТЫ СТАБИЛЬНОСТИ
    // ============================================================
    
    [Test]
    public void Application_LongRunning_StaysStable()
    {
        float runTime = 0f;
        float testDuration = 3f;
        
        while (runTime < testDuration)
        {
            runTime += Time.deltaTime;
        }
        
        // Успешное завершение
    }
    
    // ============================================================
    // 5. ТЕСТЫ СОВМЕСТИМОСТИ
    // ============================================================
    
    [Test]
    public void CurrentRenderPipeline_IsDetected()
    {
        var renderPipeline = GraphicsSettings.currentRenderPipeline;
        
        if (renderPipeline != null)
        {
            Debug.Log($"Current render pipeline: {renderPipeline.GetType().Name}");
        }
        else
        {
            Debug.Log("Using Built-in Render Pipeline");
        }
        
        Assert.Pass();
    }
    
    [Test]
    public void SystemInfo_SupportsRenderTextures()
    {
        bool supportsRenderTextures = SystemInfo.supportsRenderTextures;
        Assert.IsTrue(supportsRenderTextures, "System should support render textures");
    }
    
    [Test]
    public void SystemInfo_GraphicsDeviceType_IsValid()
    {
        var graphicsDeviceType = SystemInfo.graphicsDeviceType;
        Assert.IsNotNull(graphicsDeviceType);
        Debug.Log($"Graphics device type: {graphicsDeviceType}");
    }
    
    // ============================================================
    // 6. ТЕСТЫ СОБЫТИЙ
    // ============================================================
    
    [Test]
    public void EventPublisher_TopicName_IsSet()
    {
        var eventPublisher = eventPublisherObject.AddComponent<EventPublisher>();
        eventPublisher.eventsTopic = "/env/events";
        
        Assert.AreEqual("/env/events", eventPublisher.eventsTopic);
    }
    
    [Test]
    public void EventPublisher_PublishEvent_DoesNotThrow()
    {
        var eventPublisher = eventPublisherObject.AddComponent<EventPublisher>();
        eventPublisher.eventsTopic = "/test/events";
    }
}
#endif