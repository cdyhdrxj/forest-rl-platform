import React, { useEffect, useRef, useState } from "react";

import { getServerConfig, getRTCConfiguration } from "../webrtc/js/config.js";
import { createDisplayStringArray } from "../webrtc/js/stats.js";
import { VideoPlayer } from "../webrtc/js/videoplayer.js";
import { RenderStreaming } from "../webrtc/module/renderstreaming.js";
import { Signaling, WebSocketSignaling } from "../webrtc/module/signaling.js";

const ActionType = {
  ChangeLabel: 0
};

export default function RenderStreamingPage() {
  const playerRef = useRef(null);
  const codecRef = useRef(null);
  const messageRef = useRef(null);
  const lockMouseRef = useRef(null);
  const warningRef = useRef(null);

  const playButtonRef = useRef(null);

  const renderStreamingRef = useRef(null);
  const videoPlayerRef = useRef(null);

  const multiplayChannelRef = useRef(null);

  const lastStatsRef = useRef(null);
  const intervalIdRef = useRef(null);

  const [useWebSocket, setUseWebSocket] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const isCleaningUpRef = useRef(false);

  const supportsSetCodecPreferences =
    window.RTCRtpTransceiver &&
    "setCodecPreferences" in window.RTCRtpTransceiver.prototype;

  /*
  =========================
  CLEANUP (ВАЖНО!)
  =========================
  */

  const cleanup = async () => {
    if (isCleaningUpRef.current) return;
    isCleaningUpRef.current = true;

    // Очищаем статистику
    if (intervalIdRef.current) {
      clearInterval(intervalIdRef.current);
      intervalIdRef.current = null;
    }
    lastStatsRef.current = null;

    // Закрываем multiplay канал
    if (multiplayChannelRef.current) {
      try {
        multiplayChannelRef.current.close();
      } catch(e) {}
      multiplayChannelRef.current = null;
    }

    // Останавливаем RenderStreaming
    if (renderStreamingRef.current) {
      try {
        await renderStreamingRef.current.stop();
      } catch(e) {}
      renderStreamingRef.current = null;
    }

    // Удаляем VideoPlayer
    if (videoPlayerRef.current) {
      try {
        videoPlayerRef.current.deletePlayer();
      } catch(e) {}
      videoPlayerRef.current = null;
    }

    setIsConnected(false);
    isCleaningUpRef.current = false;
  };

  /*
  =========================
  INITIAL SETUP
  =========================
  */

  useEffect(() => {
    setup();

    window.oncontextmenu = () => false;

    const resizeHandler = () => {
      videoPlayerRef.current?.resizeVideo();
    };

    window.addEventListener("resize", resizeHandler);

    const beforeUnloadHandler = async () => {
      await cleanup();
    };
    window.addEventListener("beforeunload", beforeUnloadHandler);

    return () => {
      window.removeEventListener("resize", resizeHandler);
      window.removeEventListener("beforeunload", beforeUnloadHandler);
      cleanup(); // Важно: закрываем соединение при размонтировании
    };
  }, []);

  async function setup() {
    const res = await getServerConfig();
    setUseWebSocket(res.useWebSocket);
    showWarningIfNeeded(res.startupMode);
    showCodecSelect();
    showPlayButton();
  }

  /*
  =========================
  WARNING
  =========================
  */

  function showWarningIfNeeded(startupMode) {
    if (startupMode === "private") {
      if (warningRef.current) {
        warningRef.current.innerHTML = "<h4>Warning</h4> This sample is not working on Private Mode.";
        warningRef.current.hidden = false;
      }
    }
  }

  /*
  =========================
  PLAY BUTTON
  =========================
  */

  function showPlayButton() {
    if (playButtonRef.current) return;

    const btn = document.createElement("img");
    btn.id = "playButton";
    btn.src = "../../images/Play.png";
    btn.alt = "Start Streaming";
    btn.addEventListener("click", onClickPlayButton);

    if (playerRef.current) {
      playerRef.current.appendChild(btn);
    }
    playButtonRef.current = btn;
  }

  function onClickPlayButton() {
    if (playButtonRef.current) {
      playButtonRef.current.style.display = "none";
    }

    // ВАЖНО: очищаем предыдущее соединение перед созданием нового
    const startNewConnection = async () => {
      await cleanup();
      
      // Создаем новый VideoPlayer
      videoPlayerRef.current = new VideoPlayer();
      videoPlayerRef.current.createPlayer(playerRef.current, lockMouseRef.current);
      
      await setupRenderStreaming();
    };
    
    startNewConnection();
  }

  /*
  =========================
  RENDER STREAMING
  =========================
  */

  async function setupRenderStreaming() {
    if (codecRef.current) {
      codecRef.current.disabled = true;
    }

    const signaling = new WebSocketSignaling();
    const config = getRTCConfiguration();

    const renderstreaming = new RenderStreaming(signaling, config);
    renderStreamingRef.current = renderstreaming;

    renderstreaming.onConnect = onConnect;
    renderstreaming.onDisconnect = onDisconnect;
    renderstreaming.onTrackEvent = (data) => {
      if (videoPlayerRef.current) {
        videoPlayerRef.current.addTrack(data.track);
      }
    };
    renderstreaming.onGotOffer = setCodecPreferences;

    await renderstreaming.start();
    await renderstreaming.createConnection();
  }

  /*
  =========================
  CONNECTION
  =========================
  */

  function onConnect() {
    const rs = renderStreamingRef.current;
    if (!rs) return;

    const channel = rs.createDataChannel("input");
    if (videoPlayerRef.current) {
      videoPlayerRef.current.setupInput(channel);
    }

    const multiplayChannel = rs.createDataChannel("multiplay");
    multiplayChannelRef.current = multiplayChannel;

    if (multiplayChannel) {
      multiplayChannel.onopen = onOpenMultiplayChannel;
    }

    setIsConnected(true);
    showStatsMessage();
  }

  async function onOpenMultiplayChannel() {
    await new Promise((r) => setTimeout(r, 100));
    const num = Math.floor(Math.random() * 100000);
    const json = JSON.stringify({
      type: ActionType.ChangeLabel,
      argument: String(num)
    });
    safeSend(multiplayChannelRef.current, json);
  }

  async function onDisconnect(connectionId) {
    clearStatsMessage();

    if (messageRef.current) {
      messageRef.current.style.display = "block";
      messageRef.current.innerText = `Disconnect peer on ${connectionId}.`;
    }

    await cleanup();

    if (supportsSetCodecPreferences && codecRef.current) {
      codecRef.current.disabled = false;
    }

    showPlayButton();
  }

  /*
  =========================
  CODEC
  =========================
  */

  function setCodecPreferences() {
    let selectedCodecs = null;

    if (supportsSetCodecPreferences && codecRef.current) {
      const preferredCodec = codecRef.current.options[codecRef.current.selectedIndex];

      if (preferredCodec && preferredCodec.value !== "") {
        const [mimeType, sdpFmtpLine] = preferredCodec.value.split(" ");
        const { codecs } = RTCRtpSender.getCapabilities("video");
        const selectedCodecIndex = codecs.findIndex(
          (c) => c.mimeType === mimeType && c.sdpFmtpLine === sdpFmtpLine
        );
        if (selectedCodecIndex !== -1) {
          selectedCodecs = [codecs[selectedCodecIndex]];
        }
      }
    }

    if (!selectedCodecs) return;

    const transceivers = renderStreamingRef.current
      ?.getTransceivers()
      .filter((t) => t.receiver.track.kind === "video");

    if (transceivers && transceivers.length > 0) {
      transceivers.forEach((t) => t.setCodecPreferences(selectedCodecs));
    }
  }

  function showCodecSelect() {
    if (!supportsSetCodecPreferences) {
      if (messageRef.current) {
        messageRef.current.style.display = "block";
        messageRef.current.innerHTML = `Current Browser does not support RTCRtpTransceiver.setCodecPreferences`;
      }
      return;
    }

    const codecs = RTCRtpSender.getCapabilities("video")?.codecs || [];

    codecs.forEach((codec) => {
      if (["video/red", "video/ulpfec", "video/rtx"].includes(codec.mimeType)) return;

      const option = document.createElement("option");
      option.value = (codec.mimeType + " " + (codec.sdpFmtpLine || "")).trim();
      option.innerText = option.value;

      if (codecRef.current) {
        codecRef.current.appendChild(option);
      }
    });

    if (codecRef.current) {
      codecRef.current.disabled = false;
    }
  }

  /*
  =========================
  STATS
  =========================
  */

  function showStatsMessage() {
    intervalIdRef.current = setInterval(async () => {
      if (!renderStreamingRef.current) return;

      const stats = await renderStreamingRef.current.getStats();
      if (!stats) return;

      const array = createDisplayStringArray(stats, lastStatsRef.current);
      if (array.length && messageRef.current) {
        messageRef.current.style.display = "block";
        messageRef.current.innerHTML = array.join("<br>");
      }
      lastStatsRef.current = stats;
    }, 1000);
  }

  function clearStatsMessage() {
    if (intervalIdRef.current) {
      clearInterval(intervalIdRef.current);
    }
    lastStatsRef.current = null;
    intervalIdRef.current = null;
    if (messageRef.current) {
      messageRef.current.style.display = "none";
      messageRef.current.innerHTML = "";
    }
  }

  /*
  =========================
  JSX
  =========================
  */

  return (
    <div style={{ padding: "20px" }}>
      <h2>Render Streaming</h2>

      <div style={{ marginBottom: "20px" }}>
        <strong>Status:</strong> {isConnected ? "✅ Connected" : "❌ Disconnected"}
      </div>

      <div ref={warningRef} id="warning" hidden style={{ color: "orange", marginBottom: "10px" }} />

      <div style={{ marginBottom: "10px" }}>
        <label>
          <input type="checkbox" ref={lockMouseRef} id="lockMouseCheck" />
          Lock Mouse
        </label>
      </div>

      <div style={{ marginBottom: "10px" }}>
        <span>Codec preferences:</span>
        <select ref={codecRef} id="codecPreferences" style={{ marginLeft: "10px" }} />
      </div>

      <div
        ref={playerRef}
        id="player"
        style={{
          width: "100%",
          minHeight: "400px",
          background: "#000",
          borderRadius: "8px",
          position: "relative",
          overflow: "hidden",
          marginTop: "20px"
        }}
      />

      <div ref={messageRef} id="message" style={{ marginTop: "10px", display: "none" }} />
    </div>
  );
}

function safeSend(channel, data) {
  if (!channel) return false;
  if (channel.readyState !== "open") return false;
  channel.send(data);
  return true;
}