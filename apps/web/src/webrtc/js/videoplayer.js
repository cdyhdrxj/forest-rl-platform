import { Sender, Observer } from "../module/sender.js"
import { InputRemoting } from "../module/inputremoting.js"

export class VideoPlayer {
  constructor() {
    this.playerElement = null
    this.videoElement = null

    this.sender = null
    this.inputRemoting = null
    this.inputChannel = null

    this.pointerLocked = false
    this.lastPointerLockTime = 0
  }

  createPlayer(playerElement) {
    this.playerElement = playerElement

    this.videoElement = document.createElement("video")
    this.videoElement.playsInline = true
    this.videoElement.autoplay = true

    this.videoElement.srcObject = new MediaStream()

    this.playerElement.appendChild(this.videoElement)

  }

  tryLockPointer() {
    const now = Date.now()

    // ❌ защита от SecurityError
    if (now - this.lastPointerLockTime < 1000) {
      return
    }

    if (document.pointerLockElement === this.videoElement) return

    this.lastPointerLockTime = now

    this.videoElement.requestPointerLock?.()
  }

  setupInput(channel) {
    this.inputChannel = channel

    this.sender = new Sender(this.videoElement)

    this.sender.addMouse()
    this.sender.addKeyboard()
    this.sender.addGamepad()

    if ("ontouchstart" in window) {
      this.sender.addTouchscreen()
    }

    this.inputRemoting = new InputRemoting(this.sender)

    channel.onopen = () => {
      setTimeout(() => {
        this.inputRemoting.startSending()
      }, 100)
    }

    this.inputRemoting.subscribe(new Observer(channel))
  }

  addTrack(track) {
    this.videoElement?.srcObject?.addTrack(track)
  }

  resizeVideo() {
    // если используешь — оставь свой код
  }

  deletePlayer() {
    this.inputRemoting?.stopSending?.()
    this.inputRemoting = null
    this.sender = null
    this.inputChannel = null

    if (this.playerElement) {
      this.playerElement.innerHTML = ""
    }
  }

  // 🔥 ВАЖНО: именно это нужно registerMouseEvents
  sendMsg(msg) {
    if (!this.inputChannel) return false
    if (this.inputChannel.readyState !== "open") return false

    this.inputChannel.send(msg)
    return true
  }
}