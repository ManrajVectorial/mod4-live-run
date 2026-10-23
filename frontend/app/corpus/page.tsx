"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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
    <main className="ask">
      <h1 className="page__title">Policy documents</h1>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!documents && !error && <p className="status">Loading the documents…</p>}
      {documents && (
        <>
          <ul className="documents">
            {documents.map((doc) => (
              <li key={doc.document_id} className={doc.status === "superseded" ? "document document--superseded" : "document"}>
                <Link href={`/corpus/${encodeURIComponent(doc.document_id)}`} className="document__title">
                  {doc.title}, v{doc.version}
                </Link>
                {doc.status === "superseded" && <span className="badge badge--superseded">Superseded</span>}
                <p className="document__meta">
                  Effective {doc.effective} · Owner: {doc.owner}
                  {doc.superseded_by && ` · Replaced by v${doc.superseded_by}`}
                </p>
              </li>
            ))}
          </ul>
          <p className="indexed">{indexedLabel(documents[0]?.indexed_at ?? null)}</p>
        </>
      )}
    </main>
  );
}
