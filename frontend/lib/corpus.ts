import type { CorpusDocument, DocumentResponse } from "@/lib/present";

export class CorpusError extends Error {
  constructor(
    message: string,
    readonly notFound = false,
  ) {
    super(message);
  }
}

// Same-origin through the proxy, like /api/ask. Shared with the history page.
export async function getJson(path: string, notFound = "That document isn't in the corpus."): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, { cache: "no-store" });
  } catch {
    throw new CorpusError("The service can't be reached. Check your connection and try again.");
  }
  const body = await response.json().catch(() => null);
  if (response.status === 404) throw new CorpusError(notFound, true);
  if (!response.ok) {
    const message = (body as { error?: { message?: string } } | null)?.error?.message;
    throw new CorpusError(typeof message === "string" ? message : "Something went wrong. Try again shortly.");
  }
  return body;
}

export async function listDocuments(): Promise<CorpusDocument[]> {
  const body = (await getJson("/api/corpus")) as { documents: CorpusDocument[] };
  return body.documents;
}

export async function getDocument(documentId: string): Promise<DocumentResponse> {
  return (await getJson(`/api/corpus/${encodeURIComponent(documentId)}`)) as DocumentResponse;
}
