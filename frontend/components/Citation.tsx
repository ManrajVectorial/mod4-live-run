import Link from "next/link";

import { Icon } from "@/components/Icon";
import type { CitationCard } from "@/lib/present";

// One citation as a card: document, section and version always visible (U16), a badge on
// superseded sources (U17), the passage expandable in place (U3) and a link to its
// section in the document (B4).
export function Card({ card, open = false }: { card: CitationCard; open?: boolean }) {
  return (
    <li id={card.anchorId} className={card.badge ? "card card--superseded" : "card"}>
      <div className="card__head">
        <span className="card__marker" aria-label={`Source ${card.marker}`}>
          {card.marker}
        </span>
        <div className="card__body">
          <span className="card__document">{card.document}</span>
          <span className="card__meta">
            <span>{card.section}</span>
            <span className="chip">{card.version}</span>
            {card.badge && <span className="badge badge--superseded">{card.badge}</span>}
          </span>
        </div>
      </div>
      <details open={open}>
        <summary>Show the passage</summary>
        <pre className="passage">{card.text}</pre>
      </details>
      <Link href={card.href} className="card__link">
        Open {card.section.split(" ")[0]} in the document <Icon name="arrow" />
      </Link>
    </li>
  );
}

export function CardList({ title, cards }: { title: string; cards: CitationCard[] }) {
  if (cards.length === 0) return null;
  return (
    <section aria-label={title}>
      <h3 className="section-title">{title}</h3>
      <ol className="cards">
        {cards.map((card) => (
          <Card key={card.passageId} card={card} />
        ))}
      </ol>
    </section>
  );
}
