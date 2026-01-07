

export const index = 2;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/2.CWtvAaCX.js","_app/immutable/chunks/C1FmrZbK.js","_app/immutable/chunks/CIjs2MpQ.js","_app/immutable/chunks/yfmt9j3v.js"];
export const stylesheets = ["_app/immutable/assets/2.C8bl2IxJ.css"];
export const fonts = [];
