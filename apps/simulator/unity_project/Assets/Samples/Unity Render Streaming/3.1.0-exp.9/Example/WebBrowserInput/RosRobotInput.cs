using UnityEngine;
using UnityEngine.UI;

namespace Unity.RenderStreaming.Samples
{
    class RosRobotInput : MonoBehaviour
    {
        [SerializeField] SignalingManager renderStreaming;
        [SerializeField] Transform[] cameras;

        RenderStreamingSettings settings;

        private void Awake()
        {
            settings = SampleManager.Instance.Settings;
        }

        // Start is called before the first frame update
        void Start()
        {
            if (renderStreaming.runOnAwake)
                return;

            if (settings != null)
                renderStreaming.useDefaultSettings = settings.UseDefaultSettings;
            if (settings?.SignalingSettings != null)
                renderStreaming.SetSignalingSettings(settings.SignalingSettings);
            renderStreaming.Run();
        }
    }
}