import { Card, CardList } from "@/components/Citation";
import { Icon } from "@/components/Icon";
import {
  NOTICE,
  RESULT_LOOKS,
  answerParts,
  citationCards,
  conflictView,
  degradedView,
  errorView,
  indexedLabel,
  markerHref,
  refusalView,
  resultLook,
  splitSources,
  type AskResponse,
  type Look,
} from "@/lib/present";

function Header({ look, heading }: { look: Look; heading?: string }) {
  return (
    <header className="result__header">
      <Icon name={RESULT_LOOKS[look].icon} />
      <h2 className="result__heading">{heading ?? RESULT_LOOKS[look].heading}</h2>
    </header>
  );
}

// U6 and U7 on every answered and degraded result.
function Footer({ response }: { response: AskResponse }) {
  return (
    <footer className="result__footer">
      <p>{NOTICE}</p>
      <p>{indexedLabel(response.meta.corpus_indexed_at)}</p>
    </footer>
  );
}

function AnswerText({ text, messageId }: { text: string; messageId: string }) {
  return (
    <p className="answer">
      {answerParts(text).map((part, i) =>
        "marker" in part ? (
          <a key={i} href={markerHref(messageId, part.marker)} className="answer__marker">
            {part.marker}
            <span className="visually-hidden"> (source {part.marker})</span>
          </a>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </p>
  );
}

function Answered({ response }: { response: AskResponse }) {
  const { cited, earlier } = splitSources(response.sources);
  return (
    <article className="result result--answer" aria-live="polite">
      <Header look="answer" />
      <AnswerText text={response.answer ?? ""} messageId={response.message_id} />
      <CardList title="Sources" cards={citationCards(response.message_id, cited)} />
      <CardList title="Earlier version (superseded, for reference only)" cards={citationCards(response.message_id, earlier)} />
      <Footer response={response} />
    </article>
  );
}

// D6, Q10: both policies side by side, under the escalation notice.
function Conflict({ response }: { response: AskResponse }) {
  const view = conflictView(response)!;
  const sideIds = new Set(view.sides.map((s) => s.passageId));
  const { cited, earlier } = splitSources(response.sources);
  const others = citationCards(response.message_id, cited).filter((c) => !sideIds.has(c.passageId));
  return (
    <article className="result result--conflict" aria-live="polite">
      <Header look="conflict" />
      <AnswerText text={view.body} messageId={response.message_id} />
      <div className="conflict-notice" role="note">
        <Icon name="scales" />
        <div>
          <h3 className="conflict-notice__heading">{view.heading}</h3>
          <p>
            <strong>{view.escalate}</strong>
          </p>
          <AnswerText text={view.notice.replace(view.escalate, "").trim()} messageId={response.message_id} />
        </div>
      </div>
      <section aria-label="The two policies">
        <h3 className="section-title">The two policies</h3>
        <ol className="conflict-sides">
          {view.sides.map((card) => (
            <Card key={card.passageId} card={card} open />
          ))}
        </ol>
      </section>
      <CardList title="Other sources" cards={others} />
      <CardList title="Earlier version (superseded, for reference only)" cards={citationCards(response.message_id, earlier)} />
      <Footer response={response} />
    </article>
  );
}

function Refused({ response }: { response: AskResponse }) {
  const view = refusalView(response);
  return (
    <article className="result result--refusal" role="status" aria-live="polite">
      <Header look="refusal" heading={view.heading} />
      <p>{view.message}</p>
      {view.whoToAsk.length > 0 && (
        <>
          <h3 className="section-title">Who to ask</h3>
          <ul className="who-to-ask">
            {view.whoToAsk.map((row) => (
              <li key={row.topic}>
                <span>{row.topic}</span>
                <span className="who-to-ask__team">{row.team}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </article>
  );
}

function Degraded({ response }: { response: AskResponse }) {
  const view = degradedView(response);
  return (
    <article className="result result--passages" aria-live="polite">
      <Header look="passages" heading={view.heading} />
      <p>{view.message}</p>
      <CardList title="Passages that matched" cards={view.cards} />
      <CardList title="Earlier version (superseded, for reference only)" cards={view.earlier} />
      <Footer response={response} />
    </article>
  );
}

export function Result({ response }: { response: AskResponse }) {
  const look = resultLook(response);
  if (look === "conflict") return <Conflict response={response} />;
  if (look === "refusal") return <Refused response={response} />;
  if (look === "passages") return <Degraded response={response} />;
  return <Answered response={response} />;
}

// U12: a failed request is never a blank result; it says what to try.
export function ErrorResult({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const view = errorView(message);
  return (
    <article className="result result--error" role="alert">
      <Header look="error" heading={view.heading} />
      <p>{view.message}</p>
      <h3 className="section-title">What to try</h3>
      <ul className="try-this">
        {view.tryThis.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ul>
      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </article>
  );
}

export function Thinking() {
  return (
    <div className="result result--loading" role="status" aria-live="polite">
      <span className="dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      Searching the policy documents…
    </div>
  );
}
