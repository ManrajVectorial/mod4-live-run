import Link from "next/link";

import { citationLabel, corpusHref, supersededLabel, type Source } from "@/lib/present";

// One citation: document, section and version always visible (U16); the passage text
// expands in place (U3); superseded text is always labelled (U17).
export function Citation({ source }: { source: Source }) {
  const superseded = supersededLabel(source);
  return (
    <li id={`source-${source.marker}`} className={superseded ? "citation citation--superseded" : "citation"}>
      <details>
        <summary>
          <span className="citation__marker">[{source.marker}]</span>{" "}
          <span className="citation__label">{citationLabel(source)}</span>
          {superseded && <span className="badge badge--superseded">{superseded}</span>}
        </summary>
        <pre className="citation__text">{source.text}</pre>
        <Link href={corpusHref(source)} className="citation__open">
          Open this section in the document
        </Link>
      </details>
    </li>
  );
}

export function CitationList({ title, sources }: { title: string; sources: Source[] }) {
  if (sources.length === 0) return null;
  return (
    <section className="citations" aria-label={title}>
      <h2 className="citations__title">{title}</h2>
      <ol className="citations__list">
        {sources.map((source) => (
          <Citation key={source.passage_id} source={source} />
        ))}
      </ol>
    </section>
  );
}
