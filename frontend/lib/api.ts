import type { AskResponse } from "@/lib/present";

export class AskError extends Error {}

// Same-origin: the Next.js proxy route forwards /api/* to the backend, so no CORS.
export async function ask(question: string, conversationId: string | null = null): Promise<AskResponse> {
  let response: Response;
  try {
    response = await fetch("/api/ask", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(
        conversationId ? { question, conversation_id: conversationId } : { question },
      ),
    });
  } catch {
    throw new AskError("The service can't be reached. Check your connection and try again.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.error?.message;
    throw new AskError(typeof message === "string" ? message : "Something went wrong. Try again shortly.");
  }
  return body as AskResponse;
}
