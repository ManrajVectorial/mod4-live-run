import type { IconName } from "@/lib/present";

// Inline SVG icons (F9): no icon library. Decorative: the heading beside each icon carries
// the meaning, so every icon is hidden from screen readers.
const PATHS: Record<IconName | "arrow" | "back", string> = {
  check: "M20 6 9 17l-5-5",
  scales: "M12 3v18M5 21h14M6 7h12M6 7l-3 7a3 3 0 0 0 6 0L6 7Zm12 0-3 7a3 3 0 0 0 6 0l-3-7Z",
  stop: "M8.6 2h6.8L22 8.6v6.8L15.4 22H8.6L2 15.4V8.6L8.6 2ZM8 12h8",
  document: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Zm0 0v5h5M9 13h6M9 17h6",
  alert: "M12 3 2 20h20L12 3Zm0 7v4m0 3h.01",
  arrow: "M5 12h14m-5-5 5 5-5 5",
  back: "M19 12H5m5-5-5 5 5 5",
};

export function Icon({ name }: { name: keyof typeof PATHS }) {
  return (
    <svg
      className="icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

export function BrandMark() {
  return (
    <svg className="brand__mark" viewBox="0 0 28 28" aria-hidden="true" focusable="false">
      <rect width="28" height="28" rx="6" fill="currentColor" opacity="0.15" />
      <path
        d="M7 20V9l7-4 7 4v11M10 20v-6m4 6v-6m4 6v-6M6 20h16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
