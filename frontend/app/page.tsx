// The ask page. Task 0 is the empty ask box only: asking is wired up in F5.
export default function AskPage() {
  return (
    <main className="ask">
      <form>
        <label className="ask__label" htmlFor="question">
          Ask a policy question
        </label>
        <textarea
          id="question"
          name="question"
          className="ask__input"
          placeholder="For example: what is the approval threshold for a travel expense claim?"
        />
        <div className="ask__actions">
          <button type="submit" className="button button--primary" disabled>
            Ask
          </button>
        </div>
      </form>
    </main>
  );
}
