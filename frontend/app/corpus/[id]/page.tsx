"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { ErrorResult } from "@/components/Result";
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

  const back = (
    <Link href="/corpus" className="back-link">
      <Icon name="back" /> All policy documents
    </Link>
  );

  if (error?.notFound) {
    return (
      <main id="main" className="page">
        {back}
        <header className="page__header">
          <h1 className="page__title">Document not found</h1>
          <p className="page__lead">There is no document called “{id}” in the corpus.</p>
        </header>
      </main>
    );
  }
  if (error) {
    return (
      <main id="main" className="page">
        {back}
        <h1 className="visually-hidden">Policy document</h1>
        <ErrorResult message={error.message} />
      </main>
    );
  }
  if (!data) {
    return (
      <main id="main" className="page">
        {back}
        <p className="status">Loading the document…</p>
      </main>
    );
  }

  const { document: doc, current_document_id, sections } = data;
  const banner = documentBanner(doc, current_document_id);
  return (
    <main id="main" className="page">
      {back}
      <header className="page__header">
        <h1 className="page__title">{doc.title}</h1>
        <p className="list-item__meta">
          <span className="chip">v{doc.version}</span>
          {banner ? (
            <span className="badge badge--superseded">Superseded</span>
          ) : (
            <span className="badge badge--current">Current</span>
          )}
          <span>Effective {doc.effective}</span>
          <span aria-hidden="true">·</span>
          <span>Owner: {doc.owner}</span>
        </p>
      </header>
      {banner && (
        <p className="banner" role="note">
          <span className="badge badge--superseded">Superseded</span>
          <span>{banner.text}</span>
          <Link href={banner.href}>Open the current version</Link>
        </p>
      )}
      <nav className="toc panel" aria-label="Sections in this document">
        <h2 className="section-title">Sections</h2>
        <ol>
          {sections.map((section) => (
            <li key={section.section}>
              <a href={`#${sectionAnchor(section.section)}`}>
                §{section.section} {section.section_title}
              </a>
            </li>
          ))}
        </ol>
      </nav>
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
