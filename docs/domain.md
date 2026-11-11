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

- **Shield costs from guests** (household option, Settings → Expenses → General): guests then see only the costs
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

The backend builds the same codes (`backend/ibis/domain/pix.py`, a port tested against codes made by the
frontend), so month-close payment tasks and WhatsApp reminders can carry them.

**Public payment page**: `/pay?key=<PIX key>&name=<receiver>&amount=<30.00>&lang=<language>` shows the
same sheet (QR code + copy code) with **no sign-in**, so it can be linked from WhatsApp. Everything comes
from the link and nothing is loaded from the server. Editing the link only changes what the person
opening it pays. Messages build it from `FRONTEND_URL` (default: the first `CORS_ORIGINS` entry).

## Costs

A cost has: description (free text, or tap a premade description), optional category, amount,
date (past or future), who paid (1+), who covers (1+).

Shares are always equal: with 2 payers each paid half, with 3 coverers each covers a third.
Math is in integer cents; leftover cents go to the first people in list order, so totals add up exactly.

`source` records where a cost came from (`web`, `recurring`). Future integrations (WhatsApp, voice/AI)
should call `CostService.create(ctx, data, source="whatsapp")` so they reuse the same rules.

## Months

- A cost belongs to the month of its date. The month must exist and be **open**.
- The current and next month are created automatically: when the household is created, then by the
  scheduler (see **Scheduler** below). Since the next month always exists, a new month is there the moment it
  starts. Managers can create any other month, e.g. further in the future.
- **Fixed costs** (Settings → Expenses → Fixed costs; called "recurring costs" in the code): copied into each new month
  on their day of the month (31 becomes the last day in shorter months).
- **Add fixed costs** (month menu, calendar icon in the top bar, managers/admins): adds the fixed costs
  a month is missing, e.g. after they were adjusted. A fixed cost is skipped when the month already has a
  cost with the same description (case/space-insensitive) and amount, so clicking twice adds nothing; the
  month row is locked while adding, so even simultaneous clicks can't duplicate. Costs already in the month
  are never removed, even if their fixed cost was changed or deleted.
- **Closing**: managers close/reopen months. With auto-close (Settings → Expenses → Month close) set to N days, a month closes N days
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

- Categories and locations are **lists each household edits** (Settings → Tasks → Categories / Locations, managers). New households
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
- **Notify** (per task, all off by default), for two events: it starts expiring, and it is past due.
  The scheduler checks this every hour. The only exception is a task that is **created** (or saved with a new
  due date / expiring days) already inside its warning window or past due: it notifies right away.
  For each event, any of: **in the app** (a note to the assignees), **WhatsApp to the assignees** (their own
  number), **WhatsApp to the household groups**, **email to the assignees** (stored, not sent yet: email isn't
  built). Each event goes out once; changing the due date or the expiring days lets it go out again.
- **Private** (per task): only the assignees see the title and description. Everyone else who can see the
  task sees "Private task" with no description, and can't edit it (managers can still delete it). Group
  WhatsApp messages about a private task say "a private task" instead of the title; messages to the
  assignees themselves show it. Recurring tasks copy both settings into each task they create.
- **Month closed** (by a manager or auto-close): everyone who has to pay gets a task per transfer
  (`kind = month_payment`, category Bills if the household still has it) and a note linking to it, as set in
  **Settings → Expenses → Month close**: on/off (on by default), due N days after the close (default 3),
  expiring warning days (default 3) and the same notify options as any task (all off by default). With the
  defaults the task starts inside its warning window, so its "about to expire" notifications (if turned on)
  go out at once. The task's "Open payment" button opens that month's payment sheet. Reopening the month removes the payment tasks not done yet
  (and their notes); closing again creates fresh ones (amounts may have changed). Done tasks are kept.
  - The task saves how to pay, as it was at the close: the receiver's PIX key, the copy-and-paste code
    for the exact amount (BRL only), or their bank info text when there is no usable key. Its title is
    stored in the household's language (WhatsApp uses it); the app shows it in each person's language.
  - The task window lists the ways to pay: a direct transfer (key or bank info), the public payment page,
    and the copy-and-paste code, each with a copy button. Without any details it says to ask the receiver.
  - WhatsApp reminders list the same ways, then send the code alone in a second message so it copies
    cleanly. Household groups get them too (with "Assigned to"), when the settings send to groups.

### Recurring tasks

Managers and residents define them (Tasks → Recurring tasks): start date, every N days/weeks/months
(monthly keeps the start's day; 31 becomes the last day in shorter months), and when each copy is due:
on its scheduled date (default) or N days after it. Assign to **Everyone** (managers + residents),
**Everyone, including guests**, or chosen people. "Everyone" is resolved each time a copy is created, so it
follows who lives there.

- Copies are created by the scheduler's hourly run. Saving a definition whose schedule is already due
  creates its copy right away (and that copy notifies at once if it starts inside its warning window).
- Each run creates at most one copy, for the latest scheduled date not handled yet, so missed dates never
  pile up. A unique (recurring task, date) rule stops two simultaneous runs from creating it twice.
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

## Scheduler

Everything time-based runs in the scheduler (`backend/ibis/scheduler/`), never in a request. Opening a
household only reads. Requests do only what must happen on the spot: e.g. closing a month creates its
payment tasks, and a task created already inside its warning window notifies at once.

| Job | Every | Does |
|-----|-------|------|
| `housekeeping` | `HOUSEKEEPING_INTERVAL_MINUTES` (60), and once at API start | For each household: create the current and next month, auto-close months, create recurring task copies, send "about to expire" / "expired" notifications |
| `deliver_messages` | `WHATSAPP_SEND_INTERVAL_SECONDS` (20), only with a WhatsApp service | Send queued WhatsApp messages (with retries) |

- It runs inside the API process (one asyncio loop per job, each run in a thread with its own session).
  On Postgres an advisory lock makes sure only one process runs a job at a time, so several API instances
  are safe. One household failing doesn't stop the others.
- Everything it does is safe to repeat (each notification is sent once, each recurring copy is created once),
  so a run that comes late or twice changes nothing.
- Time-based things can lag by up to an hour: e.g. a month auto-closes in the first hour after its deadline.
- `SCHEDULER_ENABLED=false` turns it off (the tests do; they run jobs themselves).
- Run a job by hand: `python -m scheduler housekeeping` (from `backend/ibis`).
- **Adding a job**: write a function taking a database session in `scheduler/jobs.py` and add a `Job(...)`
  to `JOBS`. Keep the rules in `services/`; the job only calls them.

## WhatsApp

Sent through a separate service (`whatsapp/`, Node + [Baileys](https://github.com/WhiskeySockets/Baileys)),
which links a number the way WhatsApp Web does (QR code). It is **unofficial**: use a dedicated number,
since WhatsApp can block numbers it sees as automated.

- **Settings → WhatsApp** (managers): link the household's number (scan the QR code), unlink it, pick the
  **household groups**, send test messages, and see the latest messages and their status.
  "Send test" (to a group or a person) sends right away: the test message, then a sample payment reminder
  marked as a test (R$ 10 to the first active person with a usable PIX key, preferably not the recipient)
  and its PIX code. If nobody has a PIX key, only the test message is sent, and the screen says so.
- Each household links its own number (service session id = household id).
- **Household groups** are stored by WhatsApp group id (`...@g.us`), picked from the groups the linked number
  is in. Names can change or repeat; the id doesn't, so renaming a group breaks nothing (the saved name is
  refreshed when the list is opened). A group can be paused. Tasks asking for "household groups" go to all
  active ones; the message lists the assignees.
- **Individuals** use the number in each person's profile (`users.whatsapp`). Numbers typed without a
  country code get the household's (only BRL households for now: `+55`); the service then asks WhatsApp
  for the right id, which also handles Brazilian numbers with or without the extra 9.
- Messages are written in the household's language (`domain/messages.py`).
- **Delivery**: producers only queue rows in `outgoing_messages`; the scheduler's `deliver_messages` job sends
  them every `WHATSAPP_SEND_INTERVAL_SECONDS` (20), so a slow or offline WhatsApp never slows a request. Failures are
  retried after 1 min, 5 min, 30 min and 2 h, then marked failed; a bad number or unknown group fails at
  once. Without `WHATSAPP_SERVICE_URL` nothing is queued and Settings → WhatsApp says it's off.

Code: `backend/ibis/services/messaging_service.py`, `whatsapp_service.py`, `infrastructure/whatsapp.py`,
`whatsapp/src/`.

## Future integrations (not built yet)

- Email: tasks already store the email flags; `MessagingService._queue_email` is the place to fill in.
- Incoming WhatsApp messages: `users.whatsapp` maps a sender to a user; a bot would call the same services
  as the API.
- Voice / AI cost entry: parse the description into a `CostCreate` and call `CostService.create`.
