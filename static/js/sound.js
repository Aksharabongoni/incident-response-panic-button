/**
 * Web Audio API Sound Synthesizer for NOC Alerts
 * Runs 100% offline without needing audio files or mp3s.
 */
class SoundEngine {
  constructor() {
    this.audioCtx = null;
    this.isMuted = localStorage.getItem("noc_audio_muted") === "true";
  }

  _getAudioContext() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    }
    if (this.audioCtx && this.audioCtx.state === "suspended") {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    localStorage.setItem("noc_audio_muted", this.isMuted);
    return this.isMuted;
  }

  playPanicAlarm(durationSec = 2.4) {
    if (this.isMuted) return;
    try {
      const ctx = this._getAudioContext();
      if (!ctx) return;

      const osc = ctx.createOscillator();
      const gainNode = ctx.createGain();

      osc.type = "sawtooth";
      gainNode.gain.setValueAtTime(0.2, ctx.currentTime);

      const now = ctx.currentTime;
      for (let t = 0; t < durationSec; t += 0.3) {
        osc.frequency.setValueAtTime(750, now + t);
        osc.frequency.exponentialRampToValueAtTime(1150, now + t + 0.15);
        osc.frequency.exponentialRampToValueAtTime(750, now + t + 0.3);
      }

      gainNode.gain.setValueAtTime(0.2, now + durationSec - 0.2);
      gainNode.gain.exponentialRampToValueAtTime(0.001, now + durationSec);

      osc.connect(gainNode);
      gainNode.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + durationSec);
    } catch (e) {
      console.warn("AudioContext error:", e);
    }
  }

  playAckChime() {
    if (this.isMuted) return;
    try {
      const ctx = this._getAudioContext();
      if (!ctx) return;

      const notes = [440, 554.37, 659.25];
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const start = ctx.currentTime + idx * 0.12;

        osc.type = "sine";
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.12, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.4);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(start);
        osc.stop(start + 0.45);
      });
    } catch (e) {
      console.warn("AudioContext error:", e);
    }
  }

  playResolvedChime() {
    if (this.isMuted) return;
    try {
      const ctx = this._getAudioContext();
      if (!ctx) return;

      const notes = [523.25, 659.25, 783.99, 1046.50];
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const start = ctx.currentTime + idx * 0.15;

        osc.type = "triangle";
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.14, start);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.6);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(start);
        osc.stop(start + 0.65);
      });
    } catch (e) {
      console.warn("AudioContext error:", e);
    }
  }
}

window.soundEngine = new SoundEngine();

