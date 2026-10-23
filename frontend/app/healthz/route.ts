// The web service's own health check, for the platform (Railway). It says only that this
// Next.js server is up; it never calls the API, whose health is the API's /healthz.

export const dynamic = "force-dynamic";

export function GET(): Response {
  return Response.json({ status: "ok", service: "policy-assistant-web" });
}
