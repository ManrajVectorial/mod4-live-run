"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Result } from "@/components/Result";
import { CorpusError } from "@/lib/corpus";
import { getConversation, listConversations } from "@/lib/history";
import { historyTurns, type ConversationSummary, type Turn } from "@/lib/present";

const FAILED = "Something went wrong. Try again shortly.";
const WHEN = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" });

// /history: past conversations, newest first (REQ-C7); one opens with the answers and
// citations stored at the time, not a fresh search (REQ-C8).
function History() {
  const opened = useSearchParams().get("c");
  return opened ? <OneConversation conversationId={opened} /> : <AllConversations />;
}

function AllConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listConversations()
      .then(setConversations)
      .catch((caught) => setError(caught instanceof CorpusError ? caught.message : FAILED));
  }, []);

  return (
    <main className="ask">
      <h1 className="page__title">History</h1>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!conversations && !error && <p className="status">Loading past conversations…</p>}
      {conversations?.length === 0 && <p className="status">No conversations yet.</p>}
      {conversations && conversations.length > 0 && (
        <ul className="documents">
          {conversations.map((c) => (
            <li key={c.conversation_id} className="document">
              <Link href={`/history?c=${encodeURIComponent(c.conversation_id)}`} className="document__title">
                {c.first_question ?? "(no question)"}
              </Link>
              <p className="document__meta">
                {WHEN.format(new Date(c.updated_at))} UTC · {c.statuses.length}{" "}
                {c.statuses.length === 1 ? "answer" : "answers"} ({c.statuses.join(", ")})
              </p>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function OneConversation({ conversationId }: { conversationId: string }) {
  const [turns, setTurns] = useState<Turn[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getConversation(conversationId)
      .then((detail) => setTurns(historyTurns(detail)))
      .catch((caught) => setError(caught instanceof CorpusError ? caught.message : FAILED));
  }, [conversationId]);

  return (
    <main className="ask">
      <p>
        <Link href="/history">← All conversations</Link>
      </p>
      <h1 className="page__title">Past conversation</h1>
      <p className="status">Shown as it was answered at the time.</p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!turns && !error && <p className="status">Loading the conversation…</p>}
      {turns && (
        <ol className="turns" aria-label="Past conversation">
          {turns.map((turn) => (
            <li key={turn.response.message_id} className="turn">
              <p className="turn__question">
                <span className="turn__label">You asked:</span> {turn.question}
              </p>
              <Result response={turn.response} />
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}

export default function HistoryPage() {
  // useSearchParams needs a Suspense boundary in a client page.
  return (
    <Suspense fallback={<main className="ask"><p className="status">Loading…</p></main>}>
      <History />
    </Suspense>
  );
}
