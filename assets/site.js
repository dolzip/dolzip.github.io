"use strict";
// Public binary releases only. No tracking, storage or source-repository access.
(async () => {
  try {
    const response = await fetch("https://api.github.com/repos/dolzip/dolzip.github.io/releases/latest", {
      headers: {Accept: "application/vnd.github+json"}, signal: AbortSignal.timeout(5000)
    });
    if (!response.ok) return;
    const release = await response.json();
    if (release.draft || release.prerelease || !/^v\d+\.\d+\.\d+$/.test(release.tag_name) || !Array.isArray(release.assets)) return;
    const version = release.tag_name.slice(1);
    const asset = release.assets.find(a => a.name === `DolzipUnpack-${version}.dmg` && a.state === "uploaded" && a.size > 0);
    if (!asset) return;
    const url = new URL(asset.browser_download_url);
    const expected = `/dolzip/dolzip.github.io/releases/download/${release.tag_name}/${asset.name}`;
    if (url.origin !== "https://github.com" || url.pathname !== expected || url.search || url.hash) return;
    document.querySelectorAll(".release-download").forEach(link => {
      link.href = url.href;
      link.removeAttribute("aria-disabled");
      link.textContent = `${link.dataset.label} · ${version} · DMG`;
    });
    document.querySelectorAll(".release-status").forEach(node => { node.textContent = `Dolzip Unpack ${version} · DMG`; });
  } catch (_) {
    // A missing release, offline connection or API rate limit keeps Coming soon.
  }
})();
document.addEventListener("keydown", event => {
  if (event.key !== "Escape") return;
  const menu = document.querySelector(".languages[open]");
  if (menu) { menu.open = false; menu.querySelector("summary").focus(); }
});
