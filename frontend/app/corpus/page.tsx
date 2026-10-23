"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ErrorResult } from "@/components/Result";
import { CorpusError, listDocuments } from "@/lib/corpus";
import { indexedLabel, type CorpusDocument } from "@/lib/present";

// /corpus: every indexed document, superseded ones labelled (REQ-B1, U17).
export default function CorpusPage() {
  const [documents, setDocuments] = useState<CorpusDocument[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch((caught) =>
        setError(caught instanceof CorpusError ? caught.message : "Something went wrong. Try again shortly."),
      );
  }, []);

  return (
    <main id="main" className="page">
      <header className="page__header">
        <h1 className="page__title">Policy documents</h1>
        <p className="page__lead">Every document the assistant answers from. Superseded versions are kept for reference only.</p>
      </header>
      {error && <ErrorResult message={error} />}
      {!documents && !error && <p className="status">Loading the documents…</p>}
      {documents && (
        <>
          <ul className="list">
            {documents.map((doc) => {
              const superseded = doc.status === "superseded";
              return (
                <li key={doc.document_id} className={superseded ? "list-item list-item--superseded" : "list-item"}>
                  <h2 className="list-item__title">
                    <Link href={`/corpus/${encodeURIComponent(doc.document_id)}`}>{doc.title}</Link>
                    <span className="chip">v{doc.version}</span>
                    {superseded ? (
                      <span className="badge badge--superseded">Superseded</span>
                    ) : (
                      <span className="badge badge--current">Current</span>
                    )}
                  </h2>
                  <p className="list-item__meta">
                    <span>Effective {doc.effective}</span>
                    <span aria-hidden="true">·</span>
                    <span>Owner: {doc.owner}</span>
                    <span aria-hidden="true">·</span>
                    <span>{doc.passage_count} passages</span>
                    {doc.superseded_by && (
                      <>
                        <span aria-hidden="true">·</span>
                        <span>Replaced by v{doc.superseded_by}</span>
                      </>
                    )}
                  </p>
                </li>
              );
            })}
          </ul>
          <p className="indexed">{indexedLabel(documents[0]?.indexed_at ?? null)}</p>
        </>
      )}
    </main>
  );
}
