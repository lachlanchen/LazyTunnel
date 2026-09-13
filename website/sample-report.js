const ATTRIBUTION_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content"];
const ATTRIBUTION_VALUE = /^[\p{L}\p{N} ._/-]+$/u;

export function fitCheckHref(search, fallbackHref) {
  const incoming = new URLSearchParams(search || "");
  const target = new URL(fallbackHref);
  const accepted = new Map();

  for (const key of ATTRIBUTION_KEYS) {
    const value = String(incoming.get(key) || "").trim();
    if (value && Array.from(value).length <= 80 && ATTRIBUTION_VALUE.test(value)) {
      accepted.set(key, value);
    }
  }

  if (accepted.size === 0) return target.toString();
  for (const key of ATTRIBUTION_KEYS) target.searchParams.delete(key);
  for (const [key, value] of accepted) target.searchParams.set(key, value);
  return target.toString();
}

if (typeof document !== "undefined" && typeof window !== "undefined") {
  document.querySelectorAll("[data-fit-check-link], [data-attribution-link]").forEach((link) => {
    link.href = fitCheckHref(window.location.search, link.href);
  });
}
