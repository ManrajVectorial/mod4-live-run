"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";

import { Result } from "@/components/Result";
import { AskError, ask } from "@/lib/api";
import { EMPTY_CONVERSATION, addTurn, type Conversation } from "@/lib/present";

// The ask page (REQ-U1 to U13), with follow-ups in one conversation (F6, C3).
// Reset in the top bar reloads the page, which starts a new conversation (C6).
export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [conversation, setConversation] = useState<Conversation>(EMPTY_CONVERSATION);
  const [error, setError] = useState<string | null>(null);

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    const asked = question.trim();
    if (pending || !asked) return;
    setPending(true);
    setError(null);
    try {
      const response = await ask(asked, conversation.conversationId);
      setConversation((current) => addTurn(current, asked, response));
      setQuestion("");
    } catch (caught) {
      // Never a blank result: every failure is shown (U12).
      setError(caught instanceof AskError ? caught.message : "Something went wrong. Try again shortly.");
    } finally {
      setPending(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  const followUp = conversation.turns.length > 0;
  return (
    <main className="ask">
      <ol className="turns" aria-label="This conversation">
        {conversation.turns.map((turn) => (
          <li key={turn.response.message_id} className="turn">
            <p className="turn__question">
              <span className="turn__label">You asked:</span> {turn.question}
            </p>
            <Result response={turn.response} />
          </li>
        ))}
      </ol>

      <form onSubmit={submit}>
        <label className="ask__label" htmlFor="question">
          {followUp ? "Ask a follow-up question" : "Ask a policy question"}
        </label>
        <textarea
          id="question"
          name="question"
          className="ask__input"
          placeholder={
            followUp
              ? "For example: and does a claim of exactly that amount need it?"
              : "For example: what is the approval threshold for a travel expense claim?"
          }
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={onKeyDown}
          disabled={pending}
        />
        <div className="ask__actions">
          <button type="submit" className="button button--primary" disabled={pending || !question.trim()}>
            {pending ? "Asking…" : "Ask"}
          </button>
        </div>
      </form>

      {pending && (
        <p className="status" role="status">
          Searching the policy documents…
        </p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </main>
  );
}
