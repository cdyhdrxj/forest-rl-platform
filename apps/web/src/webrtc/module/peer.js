import * as Logger from "./logger.js";

export default class Peer extends EventTarget {
  constructor(connectionId, polite, config) {
    super();

    this.connectionId = connectionId;
    this.polite = polite;
    this.config = config;

    this.pc = new RTCPeerConnection(this.config);

    this.makingOffer = false;
    this.waitingAnswer = false;
    this.ignoreOffer = false;
    this.srdAnswerPending = false;

    this.log = str => Logger.log(`[${this.polite ? 'POLITE' : 'IMPOLITE'}] ${str}`);
    this.warn = str => Logger.warn(`[${this.polite ? 'POLITE' : 'IMPOLITE'}] ${str}`);

    this.assert_equals = window.assert_equals
      ? window.assert_equals
      : (a, b, msg) => {
          if (a !== b) throw new Error(`${msg} expected ${b} but got ${a}`);
        };

    // ======================
    // WebRTC handlers
    // ======================

    this.pc.ontrack = e => {
      this.log(`ontrack`);
      this.dispatchEvent(new CustomEvent('trackevent', { detail: e }));
    };

    this.pc.ondatachannel = e => {
      this.log(`ondatachannel`);
      this.dispatchEvent(new CustomEvent('adddatachannel', { detail: e }));
    };

    this.pc.onicecandidate = ({ candidate }) => {
      if (!candidate) return;

      this.dispatchEvent(new CustomEvent('sendcandidate', {
        detail: {
          connectionId: this.connectionId,
          candidate: candidate.candidate,
          sdpMLineIndex: candidate.sdpMLineIndex,
          sdpMid: candidate.sdpMid
        }
      }));
    };

    this.pc.onnegotiationneeded = this._onNegotiation.bind(this);

    this.pc.oniceconnectionstatechange = () => {
      this.log(`ice state: ${this.pc.iceConnectionState}`);

      if (this.pc.iceConnectionState === "disconnected") {
        this.dispatchEvent(new Event("disconnect"));
      }
    };
  }

  // ======================
  // NEGOTIATION (FIXED)
  // ======================
  async _onNegotiation() {
    try {
      // ❌ FIX: stop negotiation spam
      if (this.makingOffer || this.waitingAnswer) {
        this.log("skip negotiation (already in progress)");
        return;
      }

      this.makingOffer = true;

      this.assert_equals(this.pc.signalingState, "stable", "must be stable");

      await this.pc.setLocalDescription();

      this.waitingAnswer = true;

      this.dispatchEvent(new CustomEvent("sendoffer", {
        detail: {
          connectionId: this.connectionId,
          sdp: this.pc.localDescription.sdp
        }
      }));

    } catch (e) {
      this.log(e);
    } finally {
      this.makingOffer = false;
    }
  }

  // ======================
  // SDP handling
  // ======================
  async onGotDescription(connectionId, description) {
    if (this.connectionId !== connectionId) return;

    const isStable =
      this.pc.signalingState === "stable" ||
      (this.pc.signalingState === "have-local-offer" && this.srdAnswerPending);

    this.ignoreOffer =
      description.type === "offer" &&
      !this.polite &&
      (this.makingOffer || !isStable);

    if (this.ignoreOffer) {
      this.log("glare ignored offer");
      return;
    }

    this.waitingAnswer = false;
    this.srdAnswerPending = description.type === "answer";

    await this.pc.setRemoteDescription(description);

    this.srdAnswerPending = false;

    if (description.type === "offer") {
      await this.pc.setLocalDescription();

      this.dispatchEvent(new CustomEvent("sendanswer", {
        detail: {
          connectionId: this.connectionId,
          sdp: this.pc.localDescription.sdp
        }
      }));

    } else {
      this.dispatchEvent(new CustomEvent("ongotanswer", {
        detail: { connectionId: this.connectionId }
      }));
    }
  }

  // ======================
  // ICE candidates
  // ======================
  async onGotCandidate(connectionId, candidate) {
    if (this.connectionId !== connectionId) return;

    try {
      await this.pc.addIceCandidate(candidate);
    } catch (e) {
      if (!this.ignoreOffer) {
        this.warn(`ICE candidate rejected: ${e}`);
      }
    }
  }

  // ======================
  // API
  // ======================
  close() {
    this.connectionId = null;
    if (this.pc) {
      this.pc.close();
      this.pc = null;
    }
  }

  addTrack(connectionId, track) {
    if (this.connectionId !== connectionId) return;
    return this.pc.addTrack(track);
  }

  createDataChannel(connectionId, label) {
    if (this.connectionId !== connectionId) return;
    return this.pc.createDataChannel(label);
  }
}