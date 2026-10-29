# Ibis frontend style guide

Ibis uses Qdra's visual language (dark, calm, card-based, one accent color) with one big
difference: **Ibis is mobile-first**. Most costs are added from a phone, often one-handed.

## Inherited from Qdra
- Near-black background (`--bg-main: #080808`); content lives in cards with subtle borders.
- One accent (`--accent: #60A5FA`) for selection, navigation state and the primary action.
- Hierarchy through size and spacing, not color. Calm UI: few animations, no gradients.
- Every list has an empty state; loading states are simple text.
- Tokens live in `src/styles/tokens.css`; never hard-code colors in components.

## Mobile-first rules
- Design at 390px wide first, then enhance at `min-width` breakpoints (640px, 820px).
- Tap targets at least 40px tall. Prefer **chips** (tap to toggle) over dropdowns for short lists:
  people, categories, presets.
- Inputs use 16px text (prevents iOS zoom) and the right keyboard (`inputMode="decimal"` for money).
- The main action sits in a fixed bottom bar within thumb reach (`.bottom-bar`).
- Modals are bottom sheets on phones and centered dialogs on desktop (`.modal`).
- Tables become stacked cards on phones (`.mobile-only` / `.desktop-only`).

## Money and people
- Format money with `formatMoney(amount, currency)`; use `.num` for tabular figures.
- Positive balance (receives) = `--positive`, negative (pays) = `--negative`, always with a +/− sign
  so color is never the only signal.
- People are always listed residents first, then guests, each A–Z (the API returns them ordered).

## Charts
- Category colors come from a fixed, validated 8-color palette (assigned in order when a category is
  created; managers can change them). Uncategorized is neutral gray.
- The donut always has a legend with amounts and percentages, which doubles as the data table.
