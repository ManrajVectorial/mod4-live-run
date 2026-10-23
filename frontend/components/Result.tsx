import { CitationList } from "@/components/Citation";
import {
  NOTICE,
  answerParts,
  degradedMessage,
  indexedLabel,
  splitSources,
  type AskResponse,
} from "@/lib/present";

function Footer({ response }: { response: AskResponse }) {
  return (
    <footer className="result__footer">
      <p className="notice">{NOTICE}</p>
      <p className="indexed">{indexedLabel(response.meta.corpus_indexed_at)}</p>
    </footer>
  );
}

function Answered({ response }: { response: AskResponse }) {
  const { cited, earlier } = splitSources(response.sources);
  return (
    <article className="result result--answered" aria-live="polite">
      <h2 className="result__heading">What the policy says</h2>
      <p className="answer">
        {answerParts(response.answer ?? "").map((part, i) =>
          "marker" in part ? (
            <a key={i} href={`#source-${part.marker}`} className="answer__marker">
              [{part.marker}]
            </a>
          ) : (
            <span key={i} className="answer__text">
              {part.text}
            </span>
          ),
        )}
      </p>
      <CitationList title="Sources" sources={cited} />
      <CitationList title="Earlier version (superseded, for reference only)" sources={earlier} />
      <Footer response={response} />
    </article>
  );
}

function Refused({ response }: { response: AskResponse }) {
  return (
    <article className="result result--refused" role="status" aria-live="polite">
      <h2 className="result__heading">Not covered by the policy documents</h2>
      <p className="refusal">{response.refusal?.message}</p>
    </article>
  );
}

function Degraded({ response }: { response: AskResponse }) {
  const { cited, earlier } = splitSources(response.sources);
  return (
    <article className="result result--degraded" aria-live="polite">
      <h2 className="result__heading">Policy passages only</h2>
      <p className="degraded">
        {degradedMessage(response.degraded?.reason ?? "provider_error")}
      </p>
      <CitationList title="Passages" sources={cited} />
      <CitationList title="Earlier version (superseded, for reference only)" sources={earlier} />
      <Footer response={response} />
    </article>
  );
}

export function Result({ response }: { response: AskResponse }) {
  if (response.status === "answered") return <Answered response={response} />;
  if (response.status === "refused") return <Refused response={response} />;
  return <Degraded response={response} />;
}
