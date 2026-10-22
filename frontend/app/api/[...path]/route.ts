// Same-origin proxy: the browser calls /api/* on this site and the Next.js server forwards
// to the backend. The browser never talks to the API directly, so there is no CORS.

export const dynamic = "force-dynamic";

// Read at request time on the server. Bracket access with a variable key stops Next.js
// inlining the value at build time, so one build can point at any backend.
const API_BASE_URL_KEY = "NEXT_PUBLIC_API_BASE_URL";

type Context = { params: Promise<{ path: string[] }> };

function errorResponse(status: number, code: string, message: string): Response {
  return Response.json({ error: { code, message } }, { status });
}

async function forward(request: Request, context: Context): Promise<Response> {
  const base = process.env[API_BASE_URL_KEY];
  if (!base) {
    console.error(`proxy: ${API_BASE_URL_KEY} is not set`);
    return errorResponse(500, "internal_error", "The service is not configured.");
  }

  const { path } = await context.params;
  const incoming = new URL(request.url);
  const target = new URL(`/api/${path.map(encodeURIComponent).join("/")}`, base);
  target.search = incoming.search;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
      cache: "no-store",
    });
  } catch (error) {
    console.error(`proxy: API unreachable (${error instanceof Error ? error.name : "unknown"})`);
    return errorResponse(502, "internal_error", "The service is unavailable. Try again shortly.");
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}

export { forward as GET, forward as POST };
