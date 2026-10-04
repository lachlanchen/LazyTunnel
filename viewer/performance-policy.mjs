// Only RFB encoding preferences. Never resize a desktop or intercept input.
export const PERFORMANCE = Object.freeze({
    economy: Object.freeze({label: 'Data saver', quality: 2, compression: 7}),
    balanced: Object.freeze({label: 'Balanced', quality: 5, compression: 6}),
    sharp: Object.freeze({label: 'Sharper', quality: 8, compression: 2}),
    custom: Object.freeze({label: 'noVNC settings'}),
});

export function performanceChoice(query, saved) {
    const params = new URLSearchParams(query);
    const requested = params.get('performance');
    if (Object.hasOwn(PERFORMANCE, requested)) return requested;
    if (params.has('quality') || params.has('compression')) return 'custom';
    return Object.hasOwn(PERFORMANCE, saved) ? saved : 'balanced';
}

export function applyPerformance(rfb, name) {
    if (!rfb || !Object.hasOwn(PERFORMANCE, name) || name === 'custom') return;
    const preset = PERFORMANCE[name];
    rfb.qualityLevel = preset.quality;
    rfb.compressionLevel = preset.compression;
}
