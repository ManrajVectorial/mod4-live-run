# Follow-up evaluation set (D9 amendment)

Two-turn cases for setting the follow-up floor. Each case is a first question, then a
follow-up in the same conversation. "answer" follow-ups need the earlier question to make
sense and must be answered. "refuse" follow-ups change to a topic the corpus doesn't cover,
straight after a related policy question (the hardest case), and must be refused.

Kept here, never in `backend/corpus/` or `EVALUATION.md`.

### C1 — answer
First: What is the approval threshold for a travel expense claim?
Follow-up: And does a claim of exactly that amount need it?

### C2 — answer
First: What is the accommodation cap for a night in London?
Follow-up: And for Singapore?

### C3 — answer
First: How often do we refresh KYC for a high-risk client?
Follow-up: And for a standard-risk client?

### C4 — refuse
First: What is the approval threshold for a travel expense claim?
Follow-up: Can I expense my partner's flight?

### C5 — refuse
First: Can I fly business class on a six-hour flight?
Follow-up: How many days of paid parental leave am I entitled to?

### C6 — refuse
First: What happens if a KYC refresh is more than 90 days overdue?
Follow-up: What is our policy on cryptocurrency held by clients?
