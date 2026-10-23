import type { CorpusDocument, DocumentResponse } from "@/lib/present";

export class CorpusError extends Error {
  constructor(
    message: string,
    readonly notFound = false,
    readonly code: string | null = null,
  ) {
    super(message);
  }
}

// Same-origin through the proxy, like /api/ask. Shared with the history page.
export async function getJson(
  path: string,
  notFound: string | ((code: string | null) => string) = "That document isn't in the corpus.",
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, { cache: "no-store" });
  } catch {
    throw new CorpusError("The service can't be reached. Check your connection and try again.");
  }
  const body = await response.json().catch(() => null);
  const code = (body as { error?: { code?: string } } | null)?.error?.code;
  const errorCode = typeof code === "string" ? code : null;
  if (response.status === 404) {
    const message = typeof notFound === "function" ? notFound(errorCode) : notFound;
    throw new CorpusError(message, true, errorCode);
  }
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
