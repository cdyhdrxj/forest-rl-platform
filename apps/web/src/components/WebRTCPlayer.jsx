import { useEffect, useRef, useState, useCallback } from "react"
import { Theme, card } from "../constants/colors"

import { getRTCConfiguration } from "../webrtc/js/config.js"
import { createDisplayStringArray } from "../webrtc/js/stats.js"

import { VideoPlayer } from "../webrtc/js/videoplayer.js"

import { RenderStreaming } from "../webrtc/module/renderstreaming.js"
import { WebSocketSignaling } from "../webrtc/module/signaling.js"

import {
  registerGamepadEvents,
  registerKeyboardEvents,
  registerMouseEvents,
} from "../webrtc/js/register-events.js"

const ActionType = { ChangeLabel: 0 }
const STREAM_ASPECT = 16 / 9

export default function WebRTCPlayer() {
  const playerRef = useRef(null)
  const codecRef = useRef(null)
  const lockMouseRef = useRef(null)
  const containerRef = useRef(null)

  const renderStreamingRef = useRef(null)
  const videoPlayerRef = useRef(null)
  const multiplayChannelRef = useRef(null)

  const lastStatsRef = useRef(null)
  const intervalIdRef = useRef(null)

  const isCleaningUpRef = useRef(false)

  const [status, setStatus] = useState("idle")
  const [statsHtml, setStatsHtml] = useState("")
  const [lockMouse, setLockMouse] = useState(false)

  const [playerSize, setPlayerSize] = useState({
    width: 0,
    height: 0,
  })

  const supportsCodecPref =
    window.RTCRtpTransceiver &&
    "setCodecPreferences" in window.RTCRtpTransceiver.prototype

  const updateSize = useCallback(() => {
    if (!containerRef.current) return

    const containerWidth = containerRef.current.clientWidth
    const maxHeight = window.innerHeight * 0.7

    let width = containerWidth
    let height = width / STREAM_ASPECT

    if (height > maxHeight) {
      height = maxHeight
      width = height * STREAM_ASPECT
    }

    if (width < 320) {
      width = 320
      height = width / STREAM_ASPECT
    }

    if (height < 180) {
      height = 180
      width = height * STREAM_ASPECT
    }

    setPlayerSize({
      width: Math.floor(width),
      height: Math.floor(height),
    })
  }, [])

  const applyVideoStyles = useCallback(() => {
    if (!playerRef.current) return

    const videoElement = playerRef.current.querySelector("video")

    if (videoElement) {
      videoElement.style.width = "100%"
      videoElement.style.height = "100%"
      videoElement.style.objectFit = "contain"
      videoElement.style.display = "block"
      videoElement.style.pointerEvents = "auto"

      videoElement.tabIndex = 0
      videoElement.autoplay = true
      videoElement.playsInline = true
    }
  }, [lockMouse])

  useEffect(() => {
    updateSize()

    const handleResize = () => {
      updateSize()

      if (videoPlayerRef.current) {
        videoPlayerRef.current.resizeVideo()
      }

      applyVideoStyles()
    }

    window.addEventListener("resize", handleResize)

    const ro = new ResizeObserver(handleResize)

    if (containerRef.current) {
      ro.observe(containerRef.current)
    }

    return () => {
      window.removeEventListener("resize", handleResize)
      ro.disconnect()
    }
  }, [updateSize, applyVideoStyles])

  useEffect(() => {
    initCodecSelect()

    window.oncontextmenu = () => false

    const onResize = () => {
      videoPlayerRef.current?.resizeVideo()
      applyVideoStyles()
    }

    window.addEventListener("resize", onResize)

    return () => {
      window.removeEventListener("resize", onResize)
      cleanup()
    }
  }, [applyVideoStyles])

  function initCodecSelect() {
    if (!supportsCodecPref || !codecRef.current) return

    const codecs = RTCRtpSender.getCapabilities("video")?.codecs || []

    codecs.forEach((codec) => {
      if (
        ["video/red", "video/ulpfec", "video/rtx"].includes(codec.mimeType)
      ) {
        return
      }

      const opt = document.createElement("option")

      opt.value = (
        codec.mimeType +
        " " +
        (codec.sdpFmtpLine || "")
      ).trim()

      opt.innerText = opt.value

      codecRef.current.appendChild(opt)
    })

    codecRef.current.disabled = false
  }

  const cleanup = async () => {
    if (isCleaningUpRef.current) return

    isCleaningUpRef.current = true

    clearInterval(intervalIdRef.current)

    intervalIdRef.current = null
    lastStatsRef.current = null

    setStatsHtml("")

    if (multiplayChannelRef.current) {
      try {
        multiplayChannelRef.current.close()
      } catch {}

      multiplayChannelRef.current = null
    }

    if (renderStreamingRef.current) {
      try {
        await renderStreamingRef.current.stop()
      } catch {}

      renderStreamingRef.current = null
    }

    if (videoPlayerRef.current) {
      try {
        videoPlayerRef.current.deletePlayer()
      } catch {}

      videoPlayerRef.current = null
    }

    setStatus("idle")

    isCleaningUpRef.current = false
  }

  const handlePlay = async () => {
    await cleanup()

    setStatus("connecting")

    videoPlayerRef.current = new VideoPlayer()

    videoPlayerRef.current.createPlayer(
      playerRef.current,
      lockMouseRef.current
    )

    setTimeout(() => {
      applyVideoStyles()
    }, 100)

    if (codecRef.current) {
      codecRef.current.disabled = true
    }

    const signaling = new WebSocketSignaling()

    const config = getRTCConfiguration()

    const renderstreaming = new RenderStreaming(
      signaling,
      config
    )

    renderStreamingRef.current = renderstreaming

    renderstreaming.onConnect = onConnect
    renderstreaming.onDisconnect = onDisconnect

    renderstreaming.onTrackEvent = (data) => {
      videoPlayerRef.current?.addTrack(data.track)

      setTimeout(() => {
        applyVideoStyles()
      }, 50)
    }

    renderstreaming.onGotOffer = setCodecPreferences

    await renderstreaming.start()
    await renderstreaming.createConnection()
  }

  function onConnect() {
    const rs = renderStreamingRef.current

    if (!rs) return

    const inputCh = rs.createDataChannel("input")

    videoPlayerRef.current?.setupInput(inputCh)

    const videoElement =
      playerRef.current?.querySelector("video")

    if (videoElement) {
      registerKeyboardEvents(videoPlayerRef.current)

      registerMouseEvents(
        videoPlayerRef.current,
        videoElement
      )

      registerGamepadEvents(videoPlayerRef.current)

      videoElement.focus()

      videoElement.tabIndex = 0

      videoElement.style.pointerEvents = "auto"
    }

    const multiplayCh =
      rs.createDataChannel("multiplay")

    multiplayChannelRef.current = multiplayCh

    if (multiplayCh) {
      multiplayCh.onopen = onOpenMultiplay
    }

    setStatus("connected")

    startStats()

    applyVideoStyles()
  }

  async function onOpenMultiplay() {
    await new Promise((r) => setTimeout(r, 100))

    const num = Math.floor(Math.random() * 100000)

    const json = JSON.stringify({
      type: ActionType.ChangeLabel,
      argument: String(num),
    })

    safeSend(multiplayChannelRef.current, json)
  }

  async function onDisconnect() {
    stopStats()

    setStatus("disconnected")

    await cleanup()

    if (supportsCodecPref && codecRef.current) {
      codecRef.current.disabled = false
    }
  }

  function setCodecPreferences() {
    if (!supportsCodecPref || !codecRef.current) return

    const opt =
      codecRef.current.options[
        codecRef.current.selectedIndex
      ]

    if (!opt || opt.value === "") return

    const [mimeType, sdpFmtpLine] =
      opt.value.split(" ")

    const { codecs } =
      RTCRtpSender.getCapabilities("video")

    const idx = codecs.findIndex(
      (c) =>
        c.mimeType === mimeType &&
        c.sdpFmtpLine === sdpFmtpLine
    )

    if (idx === -1) return

    const selectedCodecs = [codecs[idx]]

    renderStreamingRef.current
      ?.getTransceivers()
      .filter(
        (t) => t.receiver.track.kind === "video"
      )
      .forEach((t) =>
        t.setCodecPreferences(selectedCodecs)
      )
  }

  function startStats() {
    intervalIdRef.current = setInterval(async () => {
      const stats =
        await renderStreamingRef.current?.getStats()

      if (!stats) return

      const arr = createDisplayStringArray(
        stats,
        lastStatsRef.current
      )

      if (arr.length) {
        setStatsHtml(arr.join("<br>"))
      }

      lastStatsRef.current = stats
    }, 1000)
  }

  function stopStats() {
    clearInterval(intervalIdRef.current)

    intervalIdRef.current = null
    lastStatsRef.current = null

    setStatsHtml("")
  }

  const statusColor = {
    idle: Theme.textMuted,
    connecting: Theme.accent,
    connected: Theme.green,
    disconnected: Theme.red,
  }[status]

  const statusLabel = {
    idle: "Ожидание",
    connecting: "Подключение…",
    connected: "Подключено",
    disconnected: "Отключено",
  }[status]

  return (
    <div
      ref={containerRef}
      style={{
        ...card,
        padding: 14,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 10,
          gap: 10,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: Theme.textPrimary,
          }}
        >
          3D Симулятор · Unity WebRTC
        </span>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            flexWrap: "wrap",
          }}
        >
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              fontSize: 10,
              color: Theme.textSecond,
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              ref={lockMouseRef}
              checked={lockMouse}
              onChange={(e) =>
                setLockMouse(e.target.checked)
              }
            />
            Lock mouse
          </label>

          {supportsCodecPref && (
            <select
              ref={codecRef}
              disabled
              style={{
                fontSize: 10,
                padding: "2px 4px",
                borderRadius: 4,
                border: `1px solid ${Theme.border}`,
                background: Theme.bg,
                color: Theme.textSecond,
              }}
            />
          )}

          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: statusColor,
              background: statusColor + "22",
              padding: "2px 8px",
              borderRadius: 99,
            }}
          >
            {statusLabel}
          </span>
        </div>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          background: "#000",
          borderRadius: Theme.radiusSm,
          border: `1px solid ${Theme.border}`,
          overflow: "hidden",
          position: "relative",
          width: "100%",
          minHeight: 200,
        }}
      >
        <div
          ref={playerRef}
          style={{
            width:
              playerSize.width > 0
                ? playerSize.width
                : "100%",

            height:
              playerSize.height > 0
                ? playerSize.height
                : "auto",

            maxWidth: "100%",
            maxHeight: "70vh",

            background: "#000",
            position: "relative",
          }}
        />

        {(status === "idle" ||
          status === "disconnected" ||
          status === "connecting") && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(0,0,0,0.5)",
            }}
          >
            {status === "connecting" ? (
              <span
                style={{
                  color: "#fff",
                  fontSize: 14,
                }}
              >
                Подключение…
              </span>
            ) : (
              <button
                onClick={handlePlay}
                style={{
                  background: Theme.accent,
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  padding: "12px 28px",
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {status === "disconnected"
                  ? "▶ Переподключиться"
                  : "▶ Запустить стрим"}
              </button>
            )}
          </div>
        )}
      </div>

      {statsHtml && (
        <div
          dangerouslySetInnerHTML={{
            __html: statsHtml,
          }}
          style={{
            marginTop: 8,
            fontSize: 10,
            color: Theme.textSecond,
            fontFamily: Theme.mono,
          }}
        />
      )}
    </div>
  )
}

function safeSend(ch, data) {
  if (!ch || ch.readyState !== "open") {
    return false
  }

  ch.send(data)

  return true
}