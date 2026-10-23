"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Conversation } from "@/components/Conversation";
import { Icon } from "@/components/Icon";
import { ErrorResult } from "@/components/Result";
import { CorpusError } from "@/lib/corpus";
import { getConversation, listConversations } from "@/lib/history";
import { historyTurns, type ConversationSummary, type Turn } from "@/lib/present";

const FAILED = "Something went wrong. Try again shortly.";
const WHEN = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" });

type Problem = { message: string; notFound: boolean };

function problem(caught: unknown): Problem {
  return caught instanceof CorpusError
    ? { message: caught.message, notFound: caught.notFound }
    : { message: FAILED, notFound: false };
}

// A 404 (history switched off, or no such conversation) is a plain notice; anything else
// is an error that says what to try (U12).
function ProblemView({ value }: { value: Problem }) {
  return value.notFound ? (
    <p className="notice-line" role="status">
      {value.message}
    </p>
  ) : (
    <ErrorResult message={value.message} />
  );
}

// /history: past conversations, newest first (REQ-C7); one opens with the answers and
// citations stored at the time, not a fresh search (REQ-C8).
function History() {
  const opened = useSearchParams().get("c");
  return opened ? <OneConversation conversationId={opened} /> : <AllConversations />;
}

function AllConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState<Problem | null>(null);

  useEffect(() => {
    listConversations()
      .then(setConversations)
      .catch((caught) => setError(problem(caught)));
  }, []);

  return (
    <main id="main" className="page">
      <header className="page__header">
        <h1 className="page__title">History</h1>
        <p className="page__lead">Past conversations, newest first, shown as they were answered.</p>
      </header>
      {error && <ProblemView value={error} />}
      {!conversations && !error && <p className="status">Loading past conversations…</p>}
      {conversations?.length === 0 && <p className="notice-line">No conversations yet.</p>}
      {conversations && conversations.length > 0 && (
        <ul className="list">
          {conversations.map((c) => (
            <li key={c.conversation_id} className="list-item">
              <h2 className="list-item__title">
                <Link href={`/history?c=${encodeURIComponent(c.conversation_id)}`}>
                  {c.first_question ?? "(no question)"}
                </Link>
              </h2>
              <p className="list-item__meta">
                <span>{WHEN.format(new Date(c.updated_at))} UTC</span>
                <span aria-hidden="true">·</span>
                <span>
                  {c.statuses.length} {c.statuses.length === 1 ? "answer" : "answers"}:
                </span>
                {c.statuses.map((status, i) => (
                  <span key={i} className={`status-chip status-chip--${status}`}>
                    {status}
                  </span>
                ))}
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
  const [error, setError] = useState<Problem | null>(null);

  useEffect(() => {
    getConversation(conversationId)
      .then((detail) => setTurns(historyTurns(detail)))
      .catch((caught) => setError(problem(caught)));
  }, [conversationId]);

  return (
    <main id="main" className="page">
      <Link href="/history" className="back-link">
        <Icon name="back" /> All conversations
      </Link>
      <header className="page__header">
        <h1 className="page__title">Past conversation</h1>
        <p className="page__lead">Shown as it was answered at the time, with the citations stored then.</p>
      </header>
      {error && <ProblemView value={error} />}
      {!turns && !error && <p className="status">Loading the conversation…</p>}
      {turns && <Conversation turns={turns} label="Past conversation" />}
    </main>
  );
}

export default function HistoryPage() {
  // useSearchParams needs a Suspense boundary in a client page.
  return (
    <Suspense
      fallback={
        <main id="main" className="page">
          <p className="status">Loading…</p>
        </main>
      }
    >
      <History />
    </Suspense>
  );
}
