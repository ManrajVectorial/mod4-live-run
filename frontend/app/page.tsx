"use client";

import { useState, type FormEvent, type KeyboardEvent } from "react";

import { Conversation } from "@/components/Conversation";
import { AskError, ask } from "@/lib/api";
import { EMPTY_CONVERSATION, addTurn, type Conversation as ConversationState } from "@/lib/present";

// The ask page (REQ-U1 to U13), as a conversation (F6, F9): questions on the right, answers
// on the left. Reset in the top bar reloads the page, which starts a new conversation (C6).
export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [conversation, setConversation] = useState<ConversationState>(EMPTY_CONVERSATION);
  const [failed, setFailed] = useState<{ question: string; message: string } | null>(null);

  async function send(asked: string) {
    if (pending || !asked) return;
    setPending(asked);
    setFailed(null);
    setQuestion("");
    try {
      const response = await ask(asked, conversation.conversationId);
      setConversation((current) => addTurn(current, asked, response));
    } catch (caught) {
      // Never a blank result: every failure is shown, with what to try (U12).
      setFailed({
        question: asked,
        message: caught instanceof AskError ? caught.message : "Something went wrong. Try again shortly.",
      });
    } finally {
      setPending(null);
    }
  }

  function submit(event?: FormEvent) {
    event?.preventDefault();
    void send(question.trim());
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  const followUp = conversation.turns.length > 0;
  return (
    <main id="main" className="page">
      <header className="page__header">
        <h1 className="page__title">Ask a policy question</h1>
        <p className="page__lead">
          Answers come only from the bank&rsquo;s policy documents, with the section and version they came from.
        </p>
      </header>

      <Conversation
        turns={conversation.turns}
        label="This conversation"
        pending={pending}
        failed={failed}
        onRetry={failed ? () => void send(failed.question) : undefined}
      />

      <form className="composer panel" onSubmit={submit}>
        <label className="composer__label" htmlFor="question">
          {followUp ? "Ask a follow-up question" : "Your question"}
        </label>
        <textarea
          id="question"
          name="question"
          className="composer__input"
          placeholder={
            followUp
              ? "For example: and does a claim of exactly that amount need it?"
              : "For example: what is the approval threshold for a travel expense claim?"
          }
          aria-describedby="question-hint"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={onKeyDown}
          disabled={pending !== null}
        />
        <div className="composer__row">
          <p id="question-hint" className="composer__hint">
            Press Enter to ask, Shift+Enter for a new line.
          </p>
          <button type="submit" className="button button--primary" disabled={pending !== null || !question.trim()}>
            {pending ? "Asking…" : "Ask"}
          </button>
        </div>
      </form>
    </main>
  );
}
