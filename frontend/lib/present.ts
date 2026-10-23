// What the ask page shows. Pure functions, so they are tested without a browser (A31).
// Shapes follow PRD §5.1.

export type Status = "answered" | "refused" | "degraded";
export type DegradedReason =
  | "generation_disabled"
  | "provider_error"
  | "provider_timeout"
  | "invalid_citations";

export type Source = {
  marker: number;
  passage_id: string;
  document_id: string;
  policy_id: string;
  title: string;
  version: string;
  status: "current" | "superseded";
  effective: string;
  superseded_by: string | null;
  section: string;
  section_title: string;
  text: string;
  score: number;
};

export type AskResponse = {
  status: Status;
  conversation_id: string;
  message_id: string;
  answer: string | null;
  refusal: { reason: "below_threshold"; message: string } | null;
  degraded: { reason: DegradedReason } | null;
  sources: Source[];
  meta: {
    prompt_version: string | null;
    model: string | null;
    top_score: number | null;
    threshold: number;
    retrieved: number;
    corpus_indexed_at: string | null;
    latency_ms: number;
  };
  created_at: string;
};

// REQ-U6. Drafted at F5 for the product owner's approval (A29).
export const NOTICE =
  "This tells you what the policy says. It is not a decision: an exception or judgement " +
  "call goes to the team that owns the policy.";

// REQ-U16: document, section number and title, and version, on every citation.
export function citationLabel(source: Source): string {
  return `${source.title}, §${source.section} ${source.section_title}, v${source.version}`;
}

// REQ-U17: superseded text always carries a label.
export function supersededLabel(source: Source): string | null {
  if (source.status !== "superseded") return null;
  return source.superseded_by
    ? `Superseded: replaced by v${source.superseded_by} on this policy`
    : "Superseded";
}

// D4 and D7: current citations in marker order, then earlier versions apart.
export function splitSources(sources: Source[]): { cited: Source[]; earlier: Source[] } {
  const byMarker = [...sources].sort((a, b) => a.marker - b.marker);
  return {
    cited: byMarker.filter((s) => s.status === "current"),
    earlier: byMarker.filter((s) => s.status === "superseded"),
  };
}

export type AnswerPart = { text: string } | { marker: number };

// "[1]" in an answer becomes a reference to citation 1.
export function answerParts(answer: string): AnswerPart[] {
  const parts: AnswerPart[] = [];
  let last = 0;
  for (const match of answer.matchAll(/\[(\d+)\]/g)) {
    const start = match.index ?? 0;
    if (start > last) parts.push({ text: answer.slice(last, start) });
    parts.push({ marker: Number(match[1]) });
    last = start + match[0].length;
  }
  if (last < answer.length) parts.push({ text: answer.slice(last) });
  return parts;
}

const DATE = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

// REQ-U7.
export function indexedLabel(iso: string | null): string {
  if (!iso) return "Policy documents: indexed date unknown";
  return `Policy documents indexed ${DATE.format(new Date(iso))}`;
}

// REQ-U5: every degraded result says plainly that no answer was composed.
export function degradedMessage(reason: DegradedReason): string {
  const why: Record<DegradedReason, string> = {
    generation_disabled: "answer writing is switched off",
    provider_error: "the answer service had a problem",
    provider_timeout: "the answer service took too long",
    invalid_citations: "an answer couldn't be tied to the policy text",
  };
  return `No answer was composed (${why[reason]}). These are the policy passages that matched your question.`;
}

// F7: browsing the indexed documents (PRD §5.2, §5.3).
export type CorpusDocument = {
  document_id: string;
  policy_id: string;
  title: string;
  version: string;
  status: "current" | "superseded";
  effective: string;
  owner: string;
  supersedes: string | null;
  superseded_by: string | null;
  superseded_on: string | null;
  passage_count: number;
  indexed_at: string | null;
};

export type CorpusSection = {
  section: string;
  section_title: string;
  heading_path: string[];
  passages: { passage_id: string; text: string }[];
};

export type DocumentResponse = {
  document: CorpusDocument;
  current_document_id: string;
  sections: CorpusSection[];
};

// REQ-U10, U14, U15: only links to pages that exist.
export const TOP_BAR_LINKS: readonly { href: string; label: string }[] = [
  { href: "/history", label: "History" },
  { href: "/corpus", label: "Corpus" },
];

export function sectionAnchor(section: string): string {
  return `section-${section}`;
}

// REQ-B4: a citation opens its section in the document.
export function corpusHref(source: Pick<Source, "document_id" | "section">): string {
  return `/corpus/${encodeURIComponent(source.document_id)}#${sectionAnchor(source.section)}`;
}

// REQ-B3 and U17: a superseded document says so and links to the current version.
export function documentBanner(
  doc: Pick<CorpusDocument, "status" | "superseded_by" | "superseded_on">,
  currentDocumentId: string,
): { text: string; href: string } | null {
  if (doc.status !== "superseded") return null;
  const when = doc.superseded_on ? `Superseded on ${DATE.format(new Date(doc.superseded_on))}` : "Superseded";
  const current = doc.superseded_by ? ` The current version is v${doc.superseded_by}.` : "";
  return {
    text: `${when}: this version is kept for reference only.${current}`,
    href: `/corpus/${encodeURIComponent(currentDocumentId)}`,
  };
}

// F6: the page keeps the conversation it is in. Reset reloads the page, which drops it (C6).
export type Turn = { question: string; response: AskResponse };
export type Conversation = { conversationId: string | null; turns: Turn[] };

export const EMPTY_CONVERSATION: Conversation = Object.freeze({
  conversationId: null,
  turns: [],
}) as Conversation;

export function addTurn(conversation: Conversation, question: string, response: AskResponse): Conversation {
  return {
    conversationId: response.conversation_id,
    turns: [...conversation.turns, { question, response }],
  };
}

// F8: history (PRD §5.4, §5.5). Sources are the snapshot stored at answer time, which
// doesn't keep `effective` or `superseded_by` (PRD §6).
export type StoredSource = Omit<Source, "effective" | "superseded_by">;

export type ConversationSummary = {
  conversation_id: string;
  created_at: string;
  updated_at: string;
  first_question: string | null;
  message_count: number;
  statuses: Status[];
};

export type StoredMessage =
  | { message_id: string; role: "user"; content: string; created_at: string }
  | (Omit<AskResponse, "conversation_id" | "sources"> & { role: "assistant"; sources: StoredSource[] });

export type ConversationDetail = { conversation_id: string; created_at: string; messages: StoredMessage[] };

// REQ-C8: a stored message is shown with the same components as a live one, from what was
// stored. A superseded snapshot keeps its plain "Superseded" label (U17).
export function historyResponse(
  conversationId: string,
  message: Extract<StoredMessage, { role: "assistant" }>,
): AskResponse {
  const { role: _role, sources, ...rest } = message;
  return {
    ...rest,
    conversation_id: conversationId,
    sources: sources.map((s) => ({ ...s, effective: "", superseded_by: null })),
  };
}

// The history page pairs each question with the answer that followed it.
export function historyTurns(detail: ConversationDetail): Turn[] {
  const turns: Turn[] = [];
  let question: string | null = null;
  for (const m of detail.messages) {
    if (m.role === "user") question = m.content;
    else turns.push({ question: question ?? "", response: historyResponse(detail.conversation_id, m) });
  }
  return turns;
}
