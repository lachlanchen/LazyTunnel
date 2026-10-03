// Pure policy; no key values, clipboard contents, screenshots or network polling.
export class IdlePolicy {
    constructor({idleMs = 120000, hiddenMs = 10000, now = Date.now()} = {}) {
        this.idleMs = idleMs;
        this.hiddenMs = hiddenMs;
        this.lastInput = now;
        this.hiddenSince = null;
        this.keepLive = false;
    }
    activity(now) { this.lastInput = now; }
    visibility(hidden, now) {
        this.hiddenSince = hidden ? (this.hiddenSince ?? now) : null;
    }
    reason(now) {
        if (this.hiddenSince !== null && now - this.hiddenSince >= this.hiddenMs) return 'hidden';
        if (!this.keepLive && now - this.lastInput >= this.idleMs) return 'idle';
        return null;
    }
}
