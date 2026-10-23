"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CorpusError, getDocument } from "@/lib/corpus";
import { documentBanner, sectionAnchor, type DocumentResponse } from "@/lib/present";

// /corpus/[id]: one document, section by section (REQ-B2), with a superseded banner
// linking to the current version (B3) and a not-found page for unknown ids (B5).
export default function DocumentPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const [data, setData] = useState<DocumentResponse | null>(null);
  const [error, setError] = useState<CorpusError | null>(null);

  useEffect(() => {
    getDocument(id)
      .then(setData)
      .catch((caught) =>
        setError(caught instanceof CorpusError ? caught : new CorpusError("Something went wrong. Try again shortly.")),
      );
  }, [id]);

  // Once the sections are on the page, jump to the one a citation linked to (B4).
  useEffect(() => {
    if (data && window.location.hash) {
      document.getElementById(decodeURIComponent(window.location.hash.slice(1)))?.scrollIntoView();
    }
  }, [data]);

  if (error?.notFound) {
    return (
      <main className="ask">
        <h1 className="page__title">Document not found</h1>
        <p>There is no document called “{id}” in the corpus.</p>
        <p>
          <Link href="/corpus">See all policy documents</Link>
        </p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="ask">
        <p className="error" role="alert">
          {error.message}
        </p>
      </main>
    );
  }
  if (!data) {
    return (
      <main className="ask">
        <p className="status">Loading the document…</p>
      </main>
    );
  }

  const { document: doc, current_document_id, sections } = data;
  const banner = documentBanner(doc, current_document_id);
  return (
    <main className="ask">
      <p>
        <Link href="/corpus">All policy documents</Link>
      </p>
      <h1 className="page__title">
        {doc.title}, v{doc.version}
      </h1>
      <p className="document__meta">
        Effective {doc.effective} · Owner: {doc.owner}
      </p>
      {banner && (
        <p className="banner banner--superseded" role="note">
          <span className="badge badge--superseded">Superseded</span> {banner.text}{" "}
          <Link href={banner.href}>Open the current version</Link>
        </p>
      )}
      {sections.map((section) => (
        <section key={section.section} id={sectionAnchor(section.section)} className="doc-section">
          <h2 className="doc-section__heading">
            §{section.section} {section.section_title}
          </h2>
          {section.passages.map((passage) => (
            <pre key={passage.passage_id} className="doc-section__text">
              {passage.text}
            </pre>
          ))}
        </section>
      ))}
    </main>
  );
}
