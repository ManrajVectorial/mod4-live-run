# VectorForge Linear Ticket Template

> *The canonical template for every ticket created in the VectorForge Feature Pipeline. Aligned with [VFS Phase 4 — FORMALIZE](https://www.notion.so/vectorforge-framework#Part%208:%20VectorForge%20Feature%20Spec%20(VFS)) and gated by the [VectorForge Estimation Framework (VFE)](https://www.notion.so/vectorforge-estimation-framework).*
> 

## Purpose

Standardize ticket creation across all VectorForge products so that every ticket entering the Feature Pipeline carries enough context for AI-led development, proper VFE estimation, and clear acceptance criteria. A ticket following this template satisfies the **Backlog → Todo gate** requirements.

## When to Use

Use this template for all ticket types that enter the VectorForge Feature Pipeline:

| Type | Template Sections Used |
| --- | --- |
| **Feature** | All sections. Full VFE rubric (C+S+U with SLC/3Cs/AL multipliers) |
| **Enhancement** | All sections. Full VFE rubric |
| **Bug** | Simplified: Overview, Why This Matters, Technical Approach, Acceptance Criteria, VFE (C+U only, AL multiplier only) |
| **Tech Debt / Refactor** | All sections. Full VFE rubric. SLC defaults to SIMPLE unless polish is explicitly in scope |
| **Spike / Research** | Fixed at 2 points. Overview, Why This Matters, Acceptance Criteria only. Output = ADR or decision doc, never code |

---

## The Template

### Header Block

```
### ORIX-XXX: [Title]

**Type:** Feature | Enhancement | Bug | Tech Debt | Spike
**Priority:** P1 (Urgent) | P2 (High) | P3 (Normal) | P4 (Low)
**Labels:** `[3Cs]`, `[SLC]`, `[domain]`, `[layer]`
**Figma:** [Frame name] ([node ID]) — omit if no design reference
**Depends On:** [ticket IDs] — omit if none
**Enables:** [ticket IDs] — omit if none
```

**Label taxonomy:**

| Category | Values |
| --- | --- |
| 3Cs | `core`, `customized`, `cultivated` |
| SLC | `simple`, `lovable`, `complete` |
| Domain | `manual-mode`, `agent-mode`, `cross-mode`, `auth`, `billing`, `org-management`, `skills`, `connectors`, `plugins` |
| Layer | `frontend`, `backend`, `infra`, `full-stack` |

**Priority mapping:**

| Priority | Criteria | Response Time |
| --- | --- | --- |
| P1 — Urgent | Production broken, customer blocked, security | Same day |
| P2 — High | Current sprint/milestone, significant impact | This sprint |
| P3 — Normal | Important but can be sequenced | Next 2–4 sprints |
| P4 — Low | Nice to have, minor improvement | No timeline |

---

### VFE Estimate Block

> Required for all ticket types except Spikes (which are fixed at 2 points).
> 

### Features & Enhancements (Full Rubric)

```
#### VFE Estimate
| Axis | Score | Evidence |
|------|-------|----------|
| Complexity (C) | X/5 | [one sentence — novelty of tech, algorithmic depth] |
| Scope (S) | X/5 | [one sentence — surface area touched] |
| Uncertainty (U) | X/5 | [one sentence — unknowns, missing specs, external risk] |
| AI Leverage (AL) | X/5 | [one sentence — how much AI can deliver] |

**Calculation:**
- Base = C + S + U = X
- SLC multiplier: [SIMPLE ×1.00 | LOVABLE ×1.25 | COMPLETE ×1.50]
- 3Cs multiplier: [CORE ×1.00 | CUSTOMIZED ×1.10 | CULTIVATED ×1.20]
- AL multiplier: [AL1 ×1.00 | AL2 ×0.90 | AL3 ×0.80 | AL4 ×0.70 | AL5 ×0.60]
- Raw = X × X.XX × X.XX × X.XX = **X.XX**
- **Points: X** (Fibonacci bucket: ≤3→1, 3.1–5→2, 5.1–8→3, 8.1–13→5, 13.1–20→8, >20→SPLIT)
```

### Bugs (Simplified Rubric)

```
#### VFE Estimate (Bug)
| Axis | Score | Evidence |
|------|-------|----------|
| Complexity (C) | X/5 | [one sentence] |
| Uncertainty (U) | X/5 | [one sentence] |
| AI Leverage (AL) | X/5 | [one sentence] |

**Calculation:**
- Base = C + U = X
- AL multiplier: [ALx ×X.XX]
- Raw = X × X.XX = **X.XX**
- **Points: X** (Bug scale: ≤2→1, 2.1–4→2, 4.1–6→3, 6.1–8→5, >8→reclassify as refactor)
```

### Spikes

```
#### VFE Estimate (Spike)
**Points: 2** (fixed — timeboxed to 2 working days)
**Output:** ADR / Decision doc / Follow-up tickets — never code
```

---

### Content Sections

### Overview

> What this ticket delivers. One paragraph, clear and direct.
> 

```
#### Overview
[What is being built or changed. Include the "what" and "for whom".]
```

### Why This Matters

> The problem it solves, who it affects, and the impact of not doing it.
> 

```
#### Why This Matters
[Problem statement. Who is affected. What happens if this isn't done. Business or UX impact.]
```

### User Stories

> At least one user story per ticket. Use the standard format.
> 

```
#### User Stories
- As a [user type], I want [capability] so that [benefit].
- As a [user type], I want [capability] so that [benefit].
```

### Solution

> High-level approach — the "how" at a product/design level, not implementation detail.
> 

```
#### Solution
[Describe the solution approach. Reference Figma frames. Explain the user experience flow.]
```

### Technical Approach

> File-level change map. This feeds directly into the FDIP during Development.
> 

```
#### Technical Approach
| File | Change |
|------|--------|
| `path/to/file.tsx` | [What changes in this file] |
| `path/to/new-file.tsx` | **New** — [What this file does] |
```

### Risk Flags

> Identify risks by category. Omit categories that don't apply.
> 

```
#### Risk Flags
- **Technical:** [description]
- **Integration:** [description]
- **Performance:** [description]
- **UX:** [description]
- **Dependency:** [description]
```

### Dependencies

> Explicit dependency mapping. Critical for sequencing.
> 

```
#### Dependencies
- **Blocked by:** [ticket IDs with titles]
- **Enables:** [ticket IDs with titles]
- **Related:** [ticket IDs — not blocking, but relevant]
```

### Acceptance Criteria

> Checkbox list. Each criterion is independently testable.
> 

```
#### Acceptance Criteria
- [ ] [Specific, testable criterion]
- [ ] [Specific, testable criterion]
- [ ] [Specific, testable criterion]
```

### Visual Reference

> Figma frame reference for design-driven tickets. Omit for backend-only or infra tickets.
> 

```
#### Visual Reference
Figma frame: [Frame Name] (node [ID])
[Optional: brief description of key visual elements to implement]
```

---

## Complete Example — Feature Ticket

```markdown
### ORIX-200: Unified Adaptive Workspace Layout (2-Panel → 3-Panel Transition)

**Type:** Feature
**Priority:** P2 (High)
**Labels:** `core`, `lovable`, `manual-mode`, `frontend`
**Figma:** WORKSPACE (3:4164)
**Depends On:** ORIX-51 (Side-by-Side View — predecessor)
**Enables:** ORIX-201 (Inline Field Editing), ORIX-202 (Confidence Indicators), ORIX-203 (Source Highlighting), ORIX-204 (Chat as Native Interface)

#### VFE Estimate
| Axis | Score | Evidence |
|------|-------|----------|
| Complexity (C) | 3/5 | New adaptive layout controller with state-driven panel transitions; extends known patterns |
| Scope (S) | 3/5 | 5 new components + page rewrite across workspace module |
| Uncertainty (U) | 2/5 | Clear Figma spec; resizable panels are a known pattern with libraries available |
| AI Leverage (AL) | 4/5 | Layout scaffolding, panel components, and resize logic are highly AI-generatable |

**Calculation:**
- Base = 3 + 3 + 2 = 8
- SLC: LOVABLE ×1.25
- 3Cs: CORE ×1.00
- AL: 4 → ×0.70
- Raw = 8 × 1.25 × 1.00 × 0.70 = **7.00**
- **Points: 3** (Fibonacci bucket: 5.1–8.0 → 3)

#### Overview
Replace the current tabbed layout with an adaptive workspace that transitions from a 2-panel layout (Upload + Chat) pre-upload to a 3-panel layout (Document Preview + Extracted Data + Chat) post-upload, enabling a continuous workflow without page navigation.

#### Why This Matters
The current tabbed interface forces users to navigate between Upload, Results, and Export views — breaking flow and hiding context. The adaptive workspace keeps all relevant information visible simultaneously, reducing time-to-insight and making the extraction review process feel cohesive rather than fragmented.

#### User Stories
- As an operator, I want to see the document, extracted data, and chat in one view so that I can review and correct extractions without switching tabs.
- As a reviewer, I want resizable panels so that I can prioritize the view most relevant to my current task.

#### Solution
Implement an adaptive layout controller that detects document state (no document → uploaded → extracted) and transitions panel configuration accordingly. Use CSS Grid with draggable dividers for panel resizing.

#### Technical Approach
| File | Change |
|------|--------|
| `frontend/app/page.tsx` | Replace tabbed layout with adaptive 2→3 panel workspace |
| `frontend/components/workspace-layout.tsx` | **New** — Adaptive layout controller with state detection |
| `frontend/components/document-preview-panel.tsx` | **New** — Left panel: PDF viewer with extraction zone highlights |
| `frontend/components/extracted-data-panel.tsx` | **New** — Center panel: structured fields with confidence + inline editing |
| `frontend/components/chat-panel.tsx` | **New** — Right panel: context-aware chat linked to active document |

#### Risk Flags
- **Performance:** Rendering a full PDF + extracted data + chat simultaneously may impact performance on lower-spec machines. Lazy-load non-visible panels.
- **UX:** Panel minimum widths must be enforced to prevent content from becoming unusable at extreme resize ratios.

#### Dependencies
- **Blocked by:** ORIX-51 (Side-by-Side View — provides base 2-panel infrastructure)
- **Enables:** ORIX-201, ORIX-202, ORIX-203, ORIX-204

#### Acceptance Criteria
- [ ] Before upload: 2-panel layout — left (Upload + Templates), right (Chat with suggested queries)
- [ ] After upload: smooth transition to 3-panel — left (PDF), center (extracted data), right (chat)
- [ ] All three panels are resizable with drag handles
- [ ] Selecting a field in center highlights source in left panel PDF
- [ ] Chat panel is context-aware — references active document
- [ ] Layout works on screens ≥1280px; collapses gracefully below
- [ ] No page navigation required — entire workflow in one view

#### Visual Reference
Figma frame: WORKSPACE (node 3:4164)
3-panel layout with document viewer left, extracted fields center, chat right. Green accent on active elements.
```

---

## Checklist: Backlog → Todo Gate

Before a ticket can move from Backlog to Todo, confirm:

- [ ]  VFE estimate present with C/S/U/AL scores and one-sentence evidence each
- [ ]  SLC label applied (SIMPLE / LOVABLE / COMPLETE)
- [ ]  3Cs label applied (CORE / CUSTOMIZED / CULTIVATED)
- [ ]  AI justification stored (the VFE Estimate block satisfies this)
- [ ]  Priority set (P1–P4)
- [ ]  Acceptance criteria are specific and testable
- [ ]  Dependencies are mapped (Blocked by / Enables)

---

## Related Notes

- [vectorforge-estimation-framework](https://www.notion.so/vectorforge-estimation-framework) — Full VFE rubric, formula, calibration anchors, and worked examples
- [vectorforge-framework](https://www.notion.so/vectorforge-framework) — Parent methodology including Feature Pipeline v4, VFS process, 3Cs and SLC frameworks
- [vectorforge-framework > Part 7: Feature Pipeline v4](https://www.notion.so/vectorforge-framework#Part%207:%20Feature%20Pipeline%20v4) — The 11-stage pipeline this template feeds into
- [vectorforge-framework > Part 8: VectorForge Feature Spec (VFS)](https://www.notion.so/vectorforge-framework#Part%208:%20VectorForge%20Feature%20Spec%20(VFS)) — The 5-phase feature spec process (this template implements Phase 4: FORMALIZE)
- [orion-storming-sprint-tickets](https://www.notion.so/orion-storming-sprint-tickets) — First production usage: 38 Orion UX redesign tickets with full VFE estimation (110 points total)

---

*Vectorial · April 2026 · VectorForge Linear Ticket Template v1*