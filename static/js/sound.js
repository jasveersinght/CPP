// Synthesized Web Audio API sound generator for MATH AUCTION
// Avoids external audio file network dependencies, ensures 100% reliability

class SoundEffects {
  constructor() {
    this.audioCtx = null;
    this.soundEnabled = localStorage.getItem('math_auction_sound') !== 'false';
  }

  init() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  toggleSound() {
    this.soundEnabled = !this.soundEnabled;
    localStorage.setItem('math_auction_sound', this.soundEnabled ? 'true' : 'false');
    if (this.soundEnabled) {
      this.init();
      this.playBidSound();
    }
    return this.soundEnabled;
  }

  // Cash register / "Cha-Ching" sound on monetary reward
  playChaChing() {
    if (!this.soundEnabled) return;
    this.init();
    if (!this.audioCtx) return;

    const now = this.audioCtx.currentTime;

    // Bell 1
    const osc1 = this.audioCtx.createOscillator();
    const gain1 = this.audioCtx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(1800, now);
    osc1.frequency.exponentialRampToValueAtTime(2400, now + 0.08);
    gain1.gain.setValueAtTime(0.3, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
    osc1.connect(gain1);
    gain1.connect(this.audioCtx.destination);
    osc1.start(now);
    osc1.stop(now + 0.6);

    // Bell 2 (Higher harmonic "Ching!")
    const osc2 = this.audioCtx.createOscillator();
    const gain2 = this.audioCtx.createGain();
    osc2.type = 'triangle';
    osc2.frequency.setValueAtTime(2600, now + 0.1);
    osc2.frequency.setValueAtTime(3200, now + 0.15);
    gain2.gain.setValueAtTime(0.4, now + 0.1);
    gain2.gain.exponentialRampToValueAtTime(0.0001, now + 0.9);
    osc2.connect(gain2);
    gain2.connect(this.audioCtx.destination);
    osc2.start(now + 0.1);
    osc2.stop(now + 0.9);
  }

  // Pop / click sound on placed bid
  playBidSound() {
    if (!this.soundEnabled) return;
    this.init();
    if (!this.audioCtx) return;

    const now = this.audioCtx.currentTime;
    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(440, now);
    osc.frequency.exponentialRampToValueAtTime(880, now + 0.08);

    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.12);

    osc.connect(gain);
    gain.connect(this.audioCtx.destination);
    osc.start(now);
    osc.stop(now + 0.12);
  }

  // Warning tick for timer <= 3 seconds
  playWarningTick() {
    if (!this.soundEnabled) return;
    this.init();
    if (!this.audioCtx) return;

    const now = this.audioCtx.currentTime;
    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();

    osc.type = 'square';
    osc.frequency.setValueAtTime(800, now);

    gain.gain.setValueAtTime(0.15, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

    osc.connect(gain);
    gain.connect(this.audioCtx.destination);
    osc.start(now);
    osc.stop(now + 0.05);
  }

  // Gavel sound when auction ends
  playGavel() {
    if (!this.soundEnabled) return;
    this.init();
    if (!this.audioCtx) return;

    const now = this.audioCtx.currentTime;
    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(150, now);
    osc.frequency.exponentialRampToValueAtTime(40, now + 0.25);

    gain.gain.setValueAtTime(0.4, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

    osc.connect(gain);
    gain.connect(this.audioCtx.destination);
    osc.start(now);
    osc.stop(now + 0.25);
  }
}

window.soundFX = new SoundEffects();
