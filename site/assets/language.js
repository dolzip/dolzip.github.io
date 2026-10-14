"use strict";
(() => {
const supported = ["ko", "en", "ja", "de", "fr", "es", "it", "zh-Hans", "zh-Hant", "pt-BR", "pt-PT", "nl", "sv", "da", "nb", "fi", "pl", "cs", "hu", "ru", "uk", "ca", "af", "bg", "el", "sl", "tr", "vi", "th", "ar", "en-GB"];
let selected = "ko";
for (const raw of (navigator.languages || [navigator.language])) {
  const lang = raw.toLowerCase();
  const exact = supported.find(x => x.toLowerCase() === lang);
  if (exact) { selected = exact; break; }
  if (lang.startsWith("zh")) { selected = /hant|tw|hk|mo/.test(lang) ? "zh-Hant" : "zh-Hans"; break; }
  if (lang.startsWith("pt")) { selected = lang.includes("br") ? "pt-BR" : "pt-PT"; break; }
  if (/^(no|nb)(-|$)/.test(lang)) { selected = "nb"; break; }
  const base = supported.find(x => x === lang.split("-")[0]);
  if (base) { selected = base; break; }
}
location.replace("/" + selected + "/");
})();
