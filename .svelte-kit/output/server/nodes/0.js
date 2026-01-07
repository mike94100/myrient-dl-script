

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/fallbacks/layout.svelte.js')).default;
export const imports = ["_app/immutable/nodes/0.HpnPS7uR.js","_app/immutable/chunks/CIjs2MpQ.js","_app/immutable/chunks/yfmt9j3v.js"];
export const stylesheets = [];
export const fonts = [];
