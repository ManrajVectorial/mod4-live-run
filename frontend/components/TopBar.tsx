"use client";

// The name and Reset (REQ-U9). History and Corpus links arrive with F8 and F7 (REQ-U10).
export function TopBar() {
  return (
    <header className="topbar">
      <p className="topbar__name">Policy Assistant</p>
      <button
        type="button"
        className="button"
        onClick={() => {
          // A full reload to the ask page clears everything on screen.
          window.location.assign("/");
        }}
      >
        Reset
      </button>
    </header>
  );
}
