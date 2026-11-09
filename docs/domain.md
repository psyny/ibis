# Domain rules

## Accounts and roles

- **App admin**: creates households and can act as a manager in any household.
  The first sign-in on an empty database creates the admin.
- **Household roles** (each includes everything below it):

| Role | Can |
|------|-----|
| Manager | Everything: members, roles, categories, descriptions, starting state, months (create/close/reopen), edit/delete any cost or task |
| Resident | Add tasks (edit/delete the ones they added), complete any task, manage recurring tasks |
| Guest | Add costs; edit/delete costs they added; take part in costs ("who paid" / "who covers"); see and complete only the tasks assigned to them |
| Viewer | View only (all costs and all tasks); not part of costs; can't be assigned tasks |

The whole policy is in `backend/ibis/domain/roles.py` (`MIN_ROLE_ADD_COST`, `PARTICIPANT_ROLES`, ...).

- **Shield costs from guests** (household option, Settings → General): guests then see only the costs
  they paid, cover or added, only transfers they are part of, their own balance, and no category
  breakdown. Totals and month counts only include those costs, and other costs can't be opened by link.
  Their split is still computed from all costs, so their amounts are correct. Enforced in the API
  (`HouseholdContext.is_shielded`), not just hidden in the screen.
- People lists are ordered **residents (incl. managers) A–Z, then guests A–Z** (viewers last).
- **Disabled** members can't sign in or be picked for new costs, but stay in old costs, balances
  and statistics. A household always keeps at least one active manager.

## Languages

Each household has an interface language (Settings → General, or chosen when an admin creates it;
default English): English, Português (Brasil), Deutsch, Français, Italiano, 中文, 日本語, 한국어, हिन्दी.
Everything on screen follows it, including month names, dates and money formats. Pages outside a
household (login, My account, Tools, Admin) use the last household opened.

Translations live in `frontend/src/i18n/locales/` (one file per language; `en.ts` is the source).
TypeScript fails the build if a language misses a key, and `i18n.test.ts` checks every translation
keeps the `{placeholders}`. Error messages coming from the server are still English.

## Staying signed in

Sessions slide: a sign-in token lasts 90 days (`JWT_EXPIRATION_HOURS`) and the API sends a fresh one
(`X-Refreshed-Token` header, saved by the frontend) when it is more than a day old. Anyone who opens Ibis
at least once every 90 days stays signed in. Changing a password (yourself, a manager or an admin) and
"Sign out all other devices" (My account) bump `users.token_version`, which invalidates older tokens.
Changing `JWT_SECRET_KEY` signs everyone out once.

## Paying each other (PIX)

Each person has **bank info**: a type (`PIX` or `Other`) and a text value. People edit their own in
My account; managers and admins can edit anyone's in Settings → Members.

In the split table, tapping a transfer opens a payment sheet, but only once the month is closed (an open
month shows a "not closed yet" message instead, since amounts can still change). In a closed month, the
signed-in person's transfers are tinted green (receives) or red (pays). If the receiver's bank info is a PIX key
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

## Tasks

Household to-dos (`/h/<id>/tasks`). A task has a title, an optional description, an optional due date,
0+ assignees (managers, residents, guests; never viewers), an optional **category** and **location**, and
its own **expiring** setting: how many days before the due date it turns yellow (default 3).

- Categories and locations are **lists each household edits** (Settings → Tasks, managers). New households
  start with defaults in their language (`domain/task_labels.py`): categories Cleaning, Maintenance,
  Repair, Improvement, Bills, Shopping, Pets, Other; locations Whole house, Living room, Kitchen, Bedroom,
  Bathroom, Laundry, Office, Garage, Garden. Managers can rename or delete any of them; deleting one
  clears it from the tasks that used it. The defaults keep a `key`, so a renamed "Bills" is still used for
  payment tasks. Who can do what is in the roles table above.

- The list shows pending tasks, oldest due date first (no due date last). **Red** = past due,
  **yellow** = due within its expiring days, **green** = completed (hidden unless "Show completed tasks"
  is on). Color always comes with a text label ("Overdue by 2 days", "Due tomorrow", "Done").
  Filters: assigned to me (**on by default**), assigned to a person, category, location (both All by default),
  only tasks due this month.
  The task menu (top right) has Add task and Recurring tasks.
- One completion completes the task for everyone assigned (it records who did it).
- **Notify assignees when** (per task, both off by default): it starts expiring, and/or it is past due.
  Each note is sent once; changing the due date or the expiring days lets them go out again.
- **Month closed** (by a manager or auto-close): everyone who has to pay gets a task per transfer
  (`kind = month_payment`, category Bills if the household still has it, due 3 days after the close) and a note linking to it. The task's "Open payment"
  button opens that month's payment sheet. Reopening the month removes the payment tasks not done yet
  (and their notes); closing again creates fresh ones (amounts may have changed). Done tasks are kept.

### Recurring tasks

Managers and residents define them (Tasks → Recurring tasks): start date, every N days/weeks/months
(monthly keeps the start's day; 31 becomes the last day in shorter months), and when each copy is due:
on its scheduled date (default) or N days after it. Assign to **Everyone** (managers + residents),
**Everyone, including guests**, or chosen people. "Everyone" is resolved each time a copy is created, so it
follows who lives there.

- There is no worker: copies are created whenever someone opens the household (and at API startup),
  together with the month housekeeping and the due-date notes (`services/housekeeping.py`).
- Each run creates at most one copy, for the latest scheduled date not handled yet, so missed dates never
  pile up. A unique (recurring task, date) rule stops two simultaneous visits from creating it twice.
- **Wait until the previous one is done** (on by default): if the last copy is still open on a scheduled
  date, that date is skipped.
- A new definition whose start date is in the past creates one copy right away. Editing the schedule never
  backfills past dates. Deleting a definition keeps the tasks it created.

Code: `backend/ibis/services/task_service.py`, `recurring_task_service.py`, `domain/tasks.py`.

## Notifications

Each user has an inbox (menu → Notifications), across all their households. Every notification is a
**note**: clicking it marks it read and opens what it is about (its task, via `task_id`). Notes can be
deleted (soft: `deleted_at`, shown in the Deleted tab, can be restored). To-dos are tasks, not notifications.

- Tabs: **Inbox** (not deleted), **Deleted**.
- The bar under the top bar shows the latest 5 unread notes. The menu icon gets a dot while there are any.
- Notes come from tasks: a payment task after a month closes, and the optional "expiring" / "expired"
  notes. Completing a task marks its notes as read.
- Text for known kinds is built in the UI language from `data`; `title`/`body` hold an English fallback.

Code: `backend/ibis/services/notification_service.py`, `frontend/src/utils/notifications.ts`.

## Future integrations (not built yet)

- WhatsApp: `users.whatsapp` is stored per person, so an incoming message can be mapped to a user;
  the bot would call the same services as the API.
- Voice / AI cost entry: parse the description into a `CostCreate` and call `CostService.create`.
