"use strict";
/* Anonymous paste upload for Chaos Tree share links.
 *
 * The web apps are static, so share data has to live on some CORS-friendly
 * host. Providers are tried in order; the caller should fall back to a
 * manual "copy the JSON, paste a raw URL" flow if upload() throws. Every
 * provider is unauthenticated and returns the raw URL a viewer fetches. */
window.ChaosPaste = (function () {
  const PROVIDERS = [
    {
      name: "pastebin.ai",
      canDelete: true,
      async upload(text, opts) {
        const res = await fetch("https://pastebin.ai/api/v1/pastes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: opts.title || "Chaos Tree view",
            content: text,
            language: "plaintext",
            visibility: "unlisted",
            expiration: opts.expiration || "7d"
          })
        });
        if (!res.ok) throw new Error("HTTP " + res.status);
        const j = await res.json();
        if (!j || !j.raw_url) throw new Error("no raw url in response");
        return {
          provider: "pastebin.ai", rawUrl: j.raw_url, pageUrl: j.url || null,
          deleteToken: j.delete_token || null, expiresAt: j.expires_at || null
        };
      },
      async remove(result) {
        if (!result.deleteToken) throw new Error("no delete token");
        const m = String(result.rawUrl).match(/\/raw\/([^/?#]+)/);
        if (!m) throw new Error("could not find the paste id");
        const res = await fetch("https://pastebin.ai/api/v1/pastes/" + m[1], {
          method: "DELETE", headers: { "X-Delete-Token": result.deleteToken }
        });
        if (!res.ok && res.status !== 204) throw new Error("HTTP " + res.status);
      }
    },
    {
      name: "dpaste.com",
      canDelete: false,
      async upload(text, opts) {
        const body = new URLSearchParams();
        body.set("content", text);
        body.set("expiry_days", String(opts.days || 7));
        body.set("format", "url");
        const res = await fetch("https://dpaste.com/api/v2/", { method: "POST", body });
        if (!res.ok) throw new Error("HTTP " + res.status);
        const url = (await res.text()).trim();
        if (!/^https?:\/\/\S+$/.test(url)) throw new Error("unexpected response");
        return {
          provider: "dpaste.com", rawUrl: url.replace(/\/$/, "") + ".txt",
          pageUrl: url, deleteToken: null, expiresAt: null
        };
      },
      async remove() { throw new Error("dpaste.com pastes expire on their own"); }
    }
  ];

  async function upload(text, opts) {
    opts = opts || {};
    const errors = [];
    for (const p of PROVIDERS) {
      try { return await p.upload(text, opts); }
      catch (e) {
        const msg = e && e.message ? e.message : String(e);
        if (e && e.name === "AbortError") throw e;
        errors.push(p.name + ": " + msg);
      }
    }
    throw new Error("couldn't upload the share data (" + errors.join("; ") + ")");
  }

  function providerFor(name) {
    return PROVIDERS.find(p => p.name === name) || null;
  }
  async function remove(result) {
    const p = providerFor(result && result.provider);
    if (!p) throw new Error("unknown provider");
    return p.remove(result);
  }

  return { upload, remove, PROVIDERS };
})();
