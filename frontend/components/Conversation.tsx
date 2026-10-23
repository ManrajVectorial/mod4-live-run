import { ErrorResult, Result, Thinking } from "@/components/Result";
import type { Turn } from "@/lib/present";

function Question({ text }: { text: string }) {
  return (
    <p className="bubble bubble--user">
      <span className="bubble__label">You asked</span>
      {text}
    </p>
  );
}

// One conversation, shared by / and /history (F9): questions on the right, answers on the
// left. `pending` and `failed` are the live page's in-flight and failed questions.
export function Conversation({
  turns,
  label,
  pending = null,
  failed = null,
  onRetry,
}: {
  turns: Turn[];
  label: string;
  pending?: string | null;
  failed?: { question: string; message: string } | null;
  onRetry?: () => void;
}) {
  if (turns.length === 0 && !pending && !failed) return null;
  return (
    <ol className="conversation" aria-label={label}>
      {turns.map((turn) => (
        <li key={turn.response.message_id} className="turn">
          <Question text={turn.question} />
          <div className="turn__reply">
            <Result response={turn.response} />
          </div>
        </li>
      ))}
      {pending && (
        <li className="turn">
          <Question text={pending} />
          <div className="turn__reply">
            <Thinking />
          </div>
        </li>
      )}
      {failed && !pending && (
        <li className="turn">
          <Question text={failed.question} />
          <div className="turn__reply">
            <ErrorResult message={failed.message} onRetry={onRetry} />
          </div>
        </li>
      )}
    </ol>
  );
}
