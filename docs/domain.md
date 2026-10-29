# Domain rules

## Accounts and roles

- **App admin**: creates households and can act as a manager in any household.
  The first sign-in on an empty database creates the admin.
- **Household roles** (each includes everything below it):

| Role | Can |
|------|-----|
| Manager | Everything: members, roles, categories, descriptions, starting state, months (create/close/reopen), edit/delete any cost |
| Resident | Same as guest for now (kept separate for future rules) |
| Guest | Add costs; edit/delete costs they added; take part in costs ("who paid" / "who covers") |
| Viewer | View only; not part of costs |

The whole policy is in `backend/ibis/domain/roles.py` (`MIN_ROLE_ADD_COST`, `PARTICIPANT_ROLES`, ...).

- People lists are ordered **residents (incl. managers) A–Z, then guests A–Z** (viewers last).
- **Disabled** members can't sign in or be picked for new costs, but stay in old costs, balances
  and statistics. A household always keeps at least one active manager.

## Staying signed in

Sessions slide: a sign-in token lasts 90 days (`JWT_EXPIRATION_HOURS`) and the API sends a fresh one
(`X-Refreshed-Token` header, saved by the frontend) when it is more than a day old. Anyone who opens Ibis
at least once every 90 days stays signed in. Changing a password (yourself, a manager or an admin) and
"Sign out all other devices" (My account) bump `users.token_version`, which invalidates older tokens.
Changing `JWT_SECRET_KEY` signs everyone out once.

## Paying each other (PIX)

Each person has **bank info**: a type (`PIX` or `Other`) and a text value. People edit their own in
My account; managers and admins can edit anyone's in Settings → Members.

In the split table, tapping an amount opens a payment sheet. If the receiver's bank info is a PIX key
(and the household currency is BRL), Ibis generates a PIX QR code and a "Pix Copia e Cola" code with the
exact amount (via `react-qrcode-pix`). Keys are cleaned up first: CPF/CNPJ to digits, emails to
lower case, phones need `+55` (or parentheses) to be told apart from a CPF. Otherwise the sheet shows the
bank info text and the person's uploaded QR image. Code: `frontend/src/utils/pix.ts`.

## Costs

A cost has: description (free text, or tap a premade description), optional category, amount,
date (past or future), who paid (1+), who covers (1+).

Shares are always equal: with 2 payers each paid half, with 3 coverers each covers a third.
Math is in integer cents; leftover cents go to the first people in list order, so totals add up exactly.

`source` records where a cost came from (`web`, `recurring`). Future integrations (WhatsApp, voice/AI)
should call `CostService.create(ctx, data, source="whatsapp")` so they reuse the same rules.

## Months

- A cost belongs to the month of its date. The month must exist and be **open**.
- The current and next month are created automatically (lazily, whenever a household is opened,
  and at API startup). Managers can create any other month, e.g. further in the future.
- **Fixed costs** (Settings → Fixed costs; called "recurring costs" in the code): copied into each new month
  on their day of the month (31 becomes the last day in shorter months).
- **Add fixed costs** (month menu, calendar icon in the top bar, managers/admins): adds the fixed costs
  a month is missing, e.g. after they were adjusted. A fixed cost is skipped when the month already has a
  cost with the same description (case/space-insensitive) and amount, so clicking twice adds nothing; the
  month row is locked while adding, so even simultaneous clicks can't duplicate. Costs already in the month
  are never removed, even if their fixed cost was changed or deleted.
- **Closing**: managers close/reopen months. With auto-close set to N days, a month closes N days
  after it ends. A month a manager reopened is not auto-closed again.
- The household timezone decides when a new month starts.

## Settling up (the split table)

1. For each person: `net = paid share − covered share` (positive = receives).
2. Find the fewest transfers that bring everyone to zero. A group of k people whose balances sum
   to zero needs k − 1 transfers, so the minimum is `n − (max number of disjoint zero-sum groups)`.
   For up to 12 people with a non-zero balance this is solved exactly (bitmask DP over subsets);
   above that it falls back to the greedy "largest debtor pays largest creditor" (at most n − 1).

Example from the brief: A owes B 15, B owes C 15, C owes A 3 → A −12, B 0, C +12 → **A pays C 12**.

Code: `backend/ibis/domain/settlement.py`, tested against brute force in `tests/unit/test_settlement.py`.

## Future integrations (not built yet)

- WhatsApp: `users.whatsapp` is stored per person, so an incoming message can be mapped to a user;
  the bot would call the same services as the API.
- Voice / AI cost entry: parse the description into a `CostCreate` and call `CostService.create`.
