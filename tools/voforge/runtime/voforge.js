/* voforge runtime — browser/Node ES module for consuming a voforge pack.
 *
 *   import { voHash, VoPlayer } from "./voforge.js";
 *   const vo = new VoPlayer({ base: "vo/" });
 *   vo.say("voss", "Four drones and a rig older than I am.");
 *
 * Content-addressed lookup: file is base + voHash(who+"|"+text) + ".mp3".
 * A missing file invokes your fallback (e.g. live speechSynthesis) instead.
 */

export function voHash(s) {
  const b = new TextEncoder().encode(s);
  let h = 5381;
  for (let i = 0; i < b.length; i++) h = (Math.imul(h, 33) ^ b[i]) >>> 0;
  return h.toString(16).padStart(8, "0");
}

export class VoPlayer {
  /**
   * @param {Object} opts
   * @param {string} [opts.base="vo/"]  pack directory URL (trailing slash)
   * @param {AudioContext} [opts.ctx]   shared context (created lazily if omitted)
   * @param {AudioNode} [opts.output]   destination (defaults to ctx.destination)
   * @param {(who:string,text:string)=>void} [opts.fallback] called on missing line
   */
  constructor(opts = {}) {
    this.base = opts.base ?? "vo/";
    this.ext = opts.ext ?? "mp3";     // "wav" for an xtts-cloned pack
    this.ctx = opts.ctx ?? null;
    this.output = opts.output ?? null;
    this.fallback = opts.fallback ?? null;
    this.enabled = true;
    this.cache = new Map();
    this._token = 0;
    this._src = null;
  }

  _ensureCtx() {
    if (!this.ctx) this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  }

  url(who, text) { return this.base + voHash(who + "|" + text) + "." + this.ext; }

  /** Fetch+decode without playing (call ahead of a scene for gapless lines). */
  async preload(who, text) {
    const u = this.url(who, text);
    if (this.cache.has(u)) return true;
    try {
      const r = await fetch(u);
      if (!r.ok) return false;
      const buf = await this._ensureCtx().decodeAudioData(await r.arrayBuffer());
      this.cache.set(u, buf);
      return true;
    } catch { return false; }
  }

  /** Play a line; cancels whatever was playing. Resolves "played" | "fallback" | "off". */
  async say(who, text) {
    if (!this.enabled) return "off";
    this.stop();
    const tk = ++this._token;
    const u = this.url(who, text);
    let buf = this.cache.get(u);
    if (!buf && !(await this.preload(who, text))) {
      if (tk === this._token && this.fallback) this.fallback(who, text);
      return "fallback";
    }
    buf = this.cache.get(u);
    if (tk !== this._token) return "off";        // superseded while loading
    const ctx = this._ensureCtx();
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.output ?? ctx.destination);
    src.onended = () => { if (this._src === src) this._src = null; };
    this._src = src;
    src.start();
    return "played";
  }

  stop() {
    this._token++;
    if (this._src) { try { this._src.stop(); } catch {} this._src = null; }
  }
}
