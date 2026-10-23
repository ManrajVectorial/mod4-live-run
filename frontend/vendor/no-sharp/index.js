// Stand-in for sharp. If anything ever loads it, fail loudly rather than silently.
throw new Error(
  "sharp is replaced by an empty stand-in (its native library is LGPL). " +
    "Image optimisation is disabled in next.config.ts; do not re-enable it without approval.",
);
