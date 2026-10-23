"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";

import { Result } from "@/components/Result";
import { AskError, ask } from "@/lib/api";
import type { AskResponse } from "@/lib/present";

// The ask page (REQ-U1 to U13). One question, one result; Reset in the top bar clears it.
export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (pending || !question.trim()) return;
    setPending(true);
    setError(null);
    setResult(null);
    try {
      setResult(await ask(question));
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

  return (
    <main className="ask">
      <form onSubmit={submit}>
        <label className="ask__label" htmlFor="question">
          Ask a policy question
        </label>
        <textarea
          id="question"
          name="question"
          className="ask__input"
          placeholder="For example: what is the approval threshold for a travel expense claim?"
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
      {result && <Result response={result} />}
    </main>
  );
}
