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

// FND-9: with HISTORY_ENABLED=false the API has no history routes, so it answers a plain
// not_found. A missing conversation, with history on, is conversation_not_found.
export const HISTORY_OFF =
  "History is switched off on this service: who may see past questions hasn't been decided yet.";

export function historyNotFound(code: string | null): string {
  return code === "conversation_not_found" ? "That conversation doesn't exist." : HISTORY_OFF;
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

// F9: how each kind of result looks. Pure, so tested without a browser (lib/views.test.ts).

export type Look = "answer" | "conflict" | "refusal" | "passages" | "error";
export type IconName = "check" | "scales" | "stop" | "document" | "alert";

// Each kind has its own colour (the CSS modifier is the key), icon and heading, so none can
// be mistaken for another (U4, U5, U12).
export const RESULT_LOOKS: Record<Look, { icon: IconName; heading: string }> = {
  answer: { icon: "check", heading: "What the policy says" },
  conflict: { icon: "scales", heading: "What the policies say" },
  refusal: { icon: "stop", heading: "Not covered by the policy documents" },
  passages: { icon: "document", heading: "No answer was composed" },
  error: { icon: "alert", heading: "Something went wrong" },
};

// The first words of the D6 notice in backend/app/text/conflict.md. A test reads the
// template, so a wording change there fails the tests instead of breaking the layout.
export const CONFLICT_LEAD = "These two current policies conflict:";

export function resultLook(response: AskResponse): Exclude<Look, "error"> {
  if (response.status === "refused") return "refusal";
  if (response.status === "degraded") return "passages";
  return conflictView(response) ? "conflict" : "answer";
}

export type CitationCard = {
  anchorId: string;
  marker: number;
  document: string;
  section: string;
  version: string;
  href: string;
  badge: string | null;
  text: string;
  passageId: string;
};

// Anchors carry the message ID, so [n] in one answer never jumps to another's card (FND-4).
export function markerHref(messageId: string, marker: number): string {
  return `#${citationAnchor(messageId, marker)}`;
}

function citationAnchor(messageId: string, marker: number): string {
  return `source-${messageId}-${marker}`;
}

// U16 on every card: document, section number and title, and version. B4: the link.
export function citationCards(messageId: string, sources: Source[]): CitationCard[] {
  return [...sources]
    .sort((a, b) => a.marker - b.marker)
    .map((s) => ({
      anchorId: citationAnchor(messageId, s.marker),
      marker: s.marker,
      document: s.title,
      section: `§${s.section} ${s.section_title}`,
      version: `v${s.version}`,
      href: corpusHref(s),
      badge: supersededLabel(s),
      text: s.text,
      passageId: s.passage_id,
    }));
}

export type WhoToAsk = { topic: string; team: string };

// D5: the refusal text ends "Who to ask: expenses → Group Finance; …". It is split into a
// list for display; any other shape is shown whole.
export function refusalView(response: AskResponse): {
  heading: string;
  message: string;
  whoToAsk: WhoToAsk[];
  cards: CitationCard[];
} {
  const text = response.refusal?.message ?? "";
  const [before, after] = text.split(/\s*Who to ask:\s*/);
  const whoToAsk =
    after === undefined
      ? []
      : after
          .replace(/\.\s*$/, "")
          .split(";")
          .map((part) => part.split("→").map((x) => x.trim()))
          .filter((pair) => pair.length === 2 && pair[0] && pair[1])
          .map(([topic, team]) => ({ topic, team }));
  return {
    heading: RESULT_LOOKS.refusal.heading,
    message: whoToAsk.length ? before.trim() : text,
    whoToAsk,
    cards: [], // a refusal cites no policy (D5)
  };
}

export function degradedView(response: AskResponse): {
  heading: string;
  message: string;
  cards: CitationCard[];
  earlier: CitationCard[];
} {
  const { cited, earlier } = splitSources(response.sources);
  return {
    heading: RESULT_LOOKS.passages.heading,
    message: degradedMessage(response.degraded?.reason ?? "provider_error"),
    cards: citationCards(response.message_id, cited),
    earlier: citationCards(response.message_id, earlier),
  };
}

// U12: never a blank result; always something to try.
export function errorView(message: string): { heading: string; message: string; tryThis: string[] } {
  return {
    heading: RESULT_LOOKS.error.heading,
    message,
    tryThis: [
      "Ask the question again in a moment.",
      "If it keeps failing, the policy documents are still on the Corpus page.",
    ],
  };
}

// D6: the API appends the conflict notice to the answer. Split it off and set the two
// policies it names side by side.
export function conflictView(response: AskResponse): {
  body: string;
  heading: string;
  notice: string;
  escalate: string;
  sides: CitationCard[];
} | null {
  if (response.status !== "answered" || !response.answer) return null;
  const at = response.answer.indexOf(CONFLICT_LEAD);
  if (at === -1) return null;
  const notice = response.answer.slice(at).trim();
  const markers = [...notice.matchAll(/\[(\d+)\]/g)].map((m) => Number(m[1]));
  const cards = citationCards(response.message_id, response.sources);
  const sides = markers
    .map((n) => cards.find((c) => c.marker === n))
    .filter((c): c is CitationCard => c !== undefined);
  if (sides.length < 2) return null;
  const escalate = notice.match(/Escalate to [^.]*\./)?.[0] ?? "";
  return { body: response.answer.slice(0, at).trim(), heading: "These policies conflict", notice, escalate, sides };
}
