# MediTrack frontend: design brief

Status: **approved by the Lead on 2026-10-26 (Phase A)**, with the notes recorded in [§8](#8-decisions). DD-3 and DD-5 to DD-12 were approved as written in the MT-020 pull request (#49).
Owner: Frontend agent · Scope: `frontend/**` only

This brief turns the approved spec into concrete design decisions for the web app. On behaviour, the spec wins: [requirements](../docs/requirements.md), [acceptance criteria](../docs/acceptance-criteria.md), [the API contract](../api/openapi.yaml) and [the frontend agent prompt](../prompts/frontend-agent.md). Where this brief adds a rule the spec doesn't spell out, it is listed in [§8](#8-decisions) with the Lead's decision.

Who it's for: a caregiver checking several people's medications at 7 a.m., and an older adult (maybe with low vision, shaky hands, little tech experience) marking a dose on their own. The direction is calm, clear and trustworthy, closer to a pharmacy leaflet or GOV.UK than to a startup site: white space, dark text, one restrained accent, colour only where it means something.

## 1. Principles

1. **One job per screen, one primary action per dose card.** Today is for recording doses; setup lives on other pages. Each dose card has one filled button (**Taken**); everything else is quieter.
2. **Show only what the server confirmed.** The API decides status, local dates and local times. The UI never computes or guesses them, and never shows a dose as recorded before a 201, or a 409 for the same dose (NFR-08).
3. **Nothing important disappears on its own.** No toasts and no timed messages. Results, **Undo** and errors stay on the card or form until the person acts or the data changes.
4. **Big, calm and predictable.** All text is 18 px or larger, dose buttons are 48 px tall, content sits in one column, and the layout is the same on every visit. Every page works with a keyboard, at 200% zoom and at 320 px wide.
5. **Plain words, one name per thing, no advice.** Only "dose", "medication", "schedule", "taken" and "skipped", always meaning the same thing. No cheering, no blame, no medical guidance.

## 2. Tokens

All tokens are CSS custom properties in `src/styles/tokens.css`. Components use tokens only: no raw colours, sizes or magic numbers in component CSS.

### 2.1 Colour

Contrast ratios were calculated with the WCAG 2.1 relative-luminance formula. Targets: text ≥ 4.5:1, large text and UI parts ≥ 3:1.

| Token | Value | Used for | Checked against | Ratio |
|---|---|---|---|---|
| `--color-text` | `#1B1F23` | Body text, headings | `--color-bg` / `--color-bg-subtle` | 16.58 / 15.17 |
| `--color-text-secondary` | `#4A545E` | Dosage, hints, secondary lines | `--color-bg` / `--color-bg-subtle` | 7.72 / 7.06 |
| `--color-bg` | `#FFFFFF` | Page and cards | | |
| `--color-bg-subtle` | `#F3F5F7` | Demo banner, header band, footer | | |
| `--color-border` | `#D3D8DD` | Card outlines and dividers (decorative, never the only cue for a control) | | n/a |
| `--color-border-strong` | `#68737D` | Input, select and checkbox borders; Upcoming badge outline | `--color-bg` / `--color-bg-subtle` | 4.84 / 4.43 |
| `--color-accent` | `#0A5CA8` | Primary buttons, links, secondary-button border and text, current-page marker, Due now badge | white text on it; on `--color-bg` / `--color-bg-subtle` | 6.75; 6.75 / 6.18 |
| `--color-accent-strong` | `#07467F` | Hover and pressed states, focus ring | white text on it; on `--color-bg` | 9.58; 9.58 |
| `--color-accent-subtle` | `#E8F1FA` | Info notice background, current nav item background | `--color-text` / `--color-accent-strong` on it | 14.52 / 8.39 |
| `--color-success` | `#1D6B35` | Taken and Taken late badges, success notice bar | on `--color-success-subtle` / `--color-bg` | 5.74 / 6.55 |
| `--color-success-subtle` | `#E7F3EA` | Taken badge and success notice background | `--color-text` on it | 14.53 |
| `--color-warning` | `#8A4500` | Missed badge, stale-data notice bar | on `--color-warning-subtle` / `--color-bg` | 6.37 / 7.16 |
| `--color-warning-subtle` | `#FCF0E1` | Missed badge and warning notice background | `--color-text` on it | 14.75 |
| `--color-danger` | `#B3261E` | Error text, error bars, danger button | on `--color-bg` / `--color-bg-subtle` / `--color-danger-subtle`; white text on it | 6.54 / 5.98 / 5.62; 6.54 |
| `--color-danger-strong` | `#8C1D17` | Danger button hover and pressed | white text on it | 9.12 |
| `--color-danger-subtle` | `#FBEAE9` | Error notice background | `--color-text` on it | 14.25 |
| `--color-neutral-subtle` | `#ECEFF2` | Skipped badge, loading placeholders | `--color-text-secondary` on it | 6.69 |
| `--color-disabled-bg` | `#E3E7EB` | Buttons that are unavailable (not busy) | `--color-text-secondary` on it | 6.21 |
| `--color-focus` | `#07467F` | Focus ring (same as `--color-accent-strong`) | `--color-bg` / `--color-bg-subtle` | 9.58 / 8.77 |

The only accent is blue. Green, amber and red appear only in status badges, notices and errors, where they carry meaning. No gradients, no shadows on cards, no decorative colour.

### 2.2 Type

Font: the system stack `system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`. It needs no download, keeps the CSP simple and renders well on every platform. The Lead chose built-in fonts for v1 (no web font).

| Token | Size | Line height | Weight | Used for |
|---|---|---|---|---|
| `--font-size-body` | 1.125rem (18 px) | 1.5 | 400 | Everything by default, including hints, badges, notices and the footer. Nothing is smaller. |
| `--font-size-lead` | 1.25rem (20 px) | 1.4 | 700 | Medication name on a dose card (h3), form titles |
| `--font-size-h2` | 1.5rem (24 px) | 1.3 | 700 | Section headings |
| `--font-size-time` | 1.75rem (28 px) | 1.2 | 700, tabular figures | Dose time on a card |
| `--font-size-h1` | 1.75rem → 2rem (28 → 32 px from 37.5em) | 1.25 | 700 | Page title |
| `--font-size-stat` | 2rem (32 px) | 1.2 | 700, tabular figures | Adherence percent |

Two weights only (400, 700). Paragraphs are capped at 66 characters wide. Links are always underlined, never hover-only. Times and counts use `font-variant-numeric: tabular-nums` so columns line up.

### 2.3 Space, size, shape and layout

| Token | Value | Notes |
|---|---|---|
| `--space-1` … `--space-8` | 4, 8, 12, 16, 24, 32, 48, 64 px | 4 px base. Inside a card: `--space-4`. Between cards: `--space-3`. Between sections: `--space-6`. |
| `--target-min` | 2.75rem (44 px) | Minimum height and width of every control |
| `--target-dose` | 3rem (48 px) | Taken, Skipped, Retry and Undo on dose cards |
| `--target-gap` | 0.5rem (8 px) | Minimum space between adjacent targets. Taken and Skipped use `--space-3` (12 px) to reduce mis-taps. |
| `--radius-control` | 4 px | Buttons, inputs, badges |
| `--radius-panel` | 8 px | Dose cards, notices, dialog |
| `--border-thin` / `--border-input` / `--border-bar` | 1 / 2 / 4 px | Cards and dividers / inputs / left bar on notices and fields with errors |
| `--content-max` | 46rem (736 px) | One centred column on every page |
| `--gutter` | 16 px, 24 px from 37.5em | Page side padding |

There is one breakpoint, `37.5em` (600 px), written in `em` so it follows browser zoom. Below it, dose buttons are full width and stacked, and the navigation is a 2 × 2 grid. From 37.5em up, dose cards lay out in a row (time · details · badge and buttons) and the navigation is one row. No fixed heights on anything that holds text.

### 2.4 Focus

`:focus-visible { outline: 3px solid var(--color-focus); outline-offset: 2px; }` on every interactive element, including links, checkboxes and the skip link. Inputs also darken their border to `--color-text` on focus. The ring sits outside the element, so it is visible on the blue primary button as well as on white (9.58:1). Focus is never removed with `outline: none`.

### 2.5 Motion

`--motion-fast: 120ms ease-out`, used only for colour changes on buttons and links. Under `prefers-reduced-motion: reduce` it is `0ms`. There are no slide-ins, fades, shimmering placeholders or smooth scrolling, and nothing waits for an animation to finish.

### 2.6 Forced colours and zoom

Badges, buttons and cards carry a 1 px border (transparent where not visible) so their edges show in Windows High Contrast mode. Icons use `currentColor`. All sizes are in `rem`/`em`, so text scales with browser settings. Every page reflows to one column at 320 CSS px (400% zoom of 1280) without horizontal scrolling.

## 3. Status system

The API sends `status` and `late`. The UI maps them to a label, an icon and a colour. It never derives status itself.

| Status | From the API | Label | Icon (`lucide-react`) | Badge style | Text / background / border | Greyscale cue |
|---|---|---|---|---|---|---|
| Upcoming | `upcoming` | Upcoming | `Clock` | Outline | `--color-text-secondary` / white / 1 px `--color-border-strong` (7.72:1) | White with a thin outline, clock face |
| Due now | `due` | Due now | `BellRing` | Solid | white / `--color-accent` / none (6.75:1) | The only dark, solid badge |
| Missed | `missed` | Missed | `CircleAlert` | Heavy outline | `--color-warning` / `--color-warning-subtle` / 2 px `--color-warning` (6.37:1) | Light fill with a heavy border, exclamation mark |
| Taken | `taken`, `late: false` | Taken | `CircleCheck` | Light fill | `--color-success` / `--color-success-subtle` / none (5.74:1) | Light fill, tick in a circle |
| Taken late | `taken`, `late: true` | Taken late | `ClockCheck` | Light fill | `--color-success` / `--color-success-subtle` / none (5.74:1) | Light fill, clock with a tick, extra word "late" |
| Skipped | `skipped` | Skipped | `CircleMinus` | Light fill | `--color-text-secondary` / `--color-neutral-subtle` / none (6.69:1) | Light fill, minus sign |

- **Text and icon always.** The icon is `aria-hidden`; the label is real text. Status never depends on colour (AC-28).
- **Greyscale.** The five status colours all convert to almost the same grey (88–93 on a 0–255 scale), so colour can't separate them in greyscale. What separates them is the label, the icon shape and the badge style (solid, heavy outline, thin outline, plain fill). That is deliberate: colour only reinforces.
- A **skipped** dose with `late: true` still shows **Skipped**. The spec only labels late *taken* doses (AC-15), and adherence counts only `taken_late`.
- Icon names were checked against `lucide-react` 1.61.0, the version on npm on 2026-10-26. MT-020 re-checks them against the installed version.

## 4. Interaction and data rules

### 4.1 Today: grouping and order

Statuses come from `GET /patients/{id}/doses` (no `date`). "Log window open" means `log_window_opens_at ≤ now ≤ log_window_closes_at`, with `now` from the frontend clock module (`src/clock.ts`). That is a display check, not a status calculation; the server still enforces the window.

| Group (h2) | Contains | Buttons |
|---|---|---|
| Needs attention | `due`, plus `missed` with the log window open | Taken / Skipped |
| Later today | `upcoming` | Taken / Skipped once the window opens; before that, "You can record this from 13:00." |
| Done | `taken`, `skipped` | Undo while the window is open |
| Missed | `missed` with the log window closed (rare on Today) | None: "This dose can no longer be recorded." |

- Within a group, cards keep the API order (`scheduled_for`, then medication name). Empty groups aren't rendered.
- **Cards don't jump.** Background refreshes and recording or undoing a dose update a card's status and content, but never its position. Cards regroup only when the page is reloaded, when the person navigates away and back, or when they press the visible **Refresh** button. Cards are keyed by `schedule_id` + `scheduled_for`. Moving a card on its own would pull it out from under the person's finger and lose keyboard focus.
- **Refresh** (a secondary button under the summary line) refetches the day and regroups every card by its current status. While it runs it reads "Refreshing…" and stays in place; afterwards focus stays on it and "Doses updated." is announced politely. A dose that wasn't on screen before (for example, a schedule added elsewhere) appears at the end of its group on the next background refresh. A dose that no longer exists disappears.
- Summary line: "{recorded} of {total} doses recorded · Next: {time} {medication}", where recorded = taken + skipped and "Next" is the first `upcoming` dose in API order. "Next" is left out when nothing is upcoming. The "Next: …" part is an `inline-block`, so on a narrow screen it moves to its own line as a unit instead of breaking inside the medication name.
- The timezone line ("Times shown in Africa/Harare time.") appears only when the patient's timezone differs from the browser's (`Intl.DateTimeFormat().resolvedOptions().timeZone`). The browser timezone is used for this comparison only, never for patient data.

### 4.2 Recording and undo

1. **Taken** or **Skipped** pressed → both buttons get `disabled`, the pressed one reads "Saving…", nothing moves. A second tap does nothing, so one request is sent (AC-21).
2. **201** → refetch the day → the card shows the badge and "Taken at 08:05" with **Undo**. Focus moves to that result line (`tabindex="-1"`), not to Undo, so a second Enter can't undo by accident.
3. **409 `DUPLICATE_DOSE_LOG`** → refetch; the card shows the recorded state plus "Already recorded." as information, not an error. This also covers a retry whose first attempt had in fact been saved (AC-36).
4. **5xx, network error or timeout** → the card is not shown as recorded (NFR-08). It shows "Not recorded." plus the mapped message, the support reference, **Retry** (repeats the same status) and **Cancel** (back to Taken / Skipped). Focus moves to the message.
5. **Other 4xx** (`OUTSIDE_LOG_WINDOW`, `DOSE_NOT_PLANNED`, `MEDICATION_INACTIVE`) → the mapped message on the card, then a refetch so the buttons reflect the server's view.
6. **Undo** → "Undoing…" → `DELETE /dose-logs/{id}` → refetch → the card returns to its time-based status and buttons. "Record removed." is announced politely and focus moves to the card heading. A 404 shows the `NOT_FOUND` message and refetches.
7. **Undo is offered only while the log window is open**, so a dose can always be recorded again after an undo. Once the window closes, the card shows "Taken at 08:05" without Undo, plus one line explaining why: "Undo is no longer available because this dose can't be recorded again."

No confirmation dialog for Taken, Skipped or Undo. Undo is the safety net. There is no note field: in v1, FR-05 notes are available through the API only (issue #42).

### 4.3 Keeping data fresh

- TanStack Query owns all server state. Today refetches every 60 seconds while the tab is visible, and again when the window regains focus. Statuses change with time, and only the server may change them.
- A 60-second UI tick re-checks which cards are inside their log window, so buttons appear at 13:00 without a reload. It never changes a status.
- After any record or undo, the queries for Today, Missed doses and Daily summary for that patient are invalidated.
- If a refetch fails while data is on screen, the data stays and a warning notice says "Couldn't refresh. Showing information from 09:10." The time is when the data was last fetched, formatted in the patient's timezone. On Today, the **Refresh** button right below the notice is the way to try again; on other pages the notice carries its own **Retry**.

### 4.4 Dates and times

- **Instants** (`recorded_at`, `log_window_*`, `deactivated_at`): `Intl.DateTimeFormat('en-GB', { timeZone: patient.timezone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })`, so 06:05 UTC shows as "08:05" for Africa/Harare.
- **Calendar dates** (`date`, `local_date`, `start_date`): parsed as UTC midnight and formatted with `timeZone: 'UTC'`, so "2026-10-26" shows as "Monday 26 October" whatever the browser's timezone.
- **Times of day** (`local_time`, `times_of_day`): shown exactly as returned ("08:00").
- A **24-hour clock** everywhere, matching the schedule form and the API. The year is shown only when it differs from the patient's current year.
- **The patient's today** comes from the `date` field of the Today query (cached). It fills the Missed doses default range and the "Change schedule" default end date. Date arithmetic (today − 6 days, end date + 1 day) is done on calendar dates in UTC, so DST can't shift it.
- No `new Date()` outside `src/clock.ts`, and no browser timezone for patient data. Tests run under `TZ=Asia/Tokyo` (AC-35).

### 4.5 Errors

- Every API error is mapped from `code` to the copy in [§7.3](#73-api-errors). All 12 codes in the contract's `Problem` enum are covered, plus network error, timeout and an unknown-code fallback.
- **Where errors appear.** A page that can't load shows an ErrorState. A form shows an error summary plus messages next to its fields. A dose action shows the error on its card.
- Every server error shows "Support reference: {trace ID}", taken from the `X-Trace-Id` header, or from `trace_id` in the body if the header is missing. Network errors have no reference. The trace ID is logged to the console only in development builds.

### 4.6 Forms

- Forms open in place on their page (the routes are fixed). When a form opens, focus moves to its heading; on **Cancel**, focus returns to the button that opened it.
- Labels sit above fields, hints sit under labels, and errors sit between the hint and the field, with a 4 px red bar and `aria-invalid` / `aria-describedby`.
- On a failed submit: an error summary at the top ("There is a problem", one link per error), focus moves to it, and everything the person typed stays.
- Client-side checks mirror the contract: required fields, length limits (80 / 100 / 500), `HH:MM`, no duplicate times, at least one day, grace 0–240, end date on or after start date, Missed doses range ≤ 31 days. The server's `errors[].field` is mapped to a form field (`display_name`, `timezone`, `name`, `dosage_label`, `instructions`, `times_of_day[n]`, `days_of_week`, `start_date`, `end_date`, `grace_period_minutes`). A field that doesn't map to anything on screen shows in the summary only.
- Success messages appear as a notice above the updated content and receive focus. They stay until the next action.
- The grace period field is `type="text"` with `inputmode="numeric"`, not `type="number"`, which changes value when someone scrolls over it.
- New-patient timezone is a native `<select>` of `Intl.supportedValuesOf('timeZone')` (418 zones in current browsers; it excludes the alias `UTC`). It is preselected to the browser's timezone as a suggestion only. Underscores display as spaces.

### 4.7 Navigation and page structure

- Landmarks on every page: demo notice (`role="note"`, label "Demo notice"), `header`, `nav` (on patient pages), `main` (`id="main"`) and `footer` with the disclaimer.
- The first focusable element is the "Skip to main content" link. Each page has one `h1`, and headings run h1 → h2 (sections, groups) → h3 (cards, schedules).
- On a route change, the document title updates ("Today – Demo Patient A – MediTrack") and focus moves to the page's `h1` (`tabindex="-1"`).
- The patient switcher is a disclosure (a button that opens a list of links), not a `<select>` that navigates on change (WCAG 3.2.2). Choosing a patient keeps the current page.

## 5. Component inventory

| Component | Purpose | States | Notes |
|---|---|---|---|
| **AppShell** | Skip link, demo notice, header, patient switcher, nav, `main`, footer with Disclaimer | No patient (Patients page, Not found) · patient loading · patient loaded · patient not found (`NOT_FOUND` copy + "Go to patients", nav hidden) | Nav links use `aria-current="page"`. Current item: 4 px accent underline bar plus `--color-accent-subtle` background, so it doesn't rely on colour alone. |
| **PatientSwitcher** | Change patient without leaving the page | One patient (name only, no button) · closed · open · loading list · list error with Retry | Button has `aria-expanded`. Esc closes and returns focus. The current patient is plain text marked "(current)". |
| **DoseCard** | One planned dose on Today and Missed doses | Not yet recordable ("You can record this from…") · recordable (upcoming / due / missed) · saving · recorded (taken / taken late / skipped) with Undo · recorded without Undo (window closed) · undoing · not recorded (error + Retry / Cancel) · already recorded (info) · missed, window closed | `<article aria-labelledby>` with the medication name as h3, and `<time datetime>` for the time. Button names add context after the visible label: "Taken, Demo Med Beta at 08:30". Long names wrap (`overflow-wrap: anywhere`). |
| **StatusBadge** | Status as text + icon | Upcoming · Due now · Missed · Taken · Taken late · Skipped | See [§3](#3-status-system). Not interactive. |
| **Button** | Every action | Variants: primary, secondary, quiet, danger. States: default · hover · focus-visible · pressed · busy (label changes, `disabled`, full contrast kept) · unavailable (`--color-disabled-bg`) | Minimum 44 px. Dose buttons 48 px, full width below 37.5em. Optional icon on the left, never icon-only. Always has an explicit `type`. "Quiet" looks like an underlined link but keeps a 44 px target. |
| **Field** | Labelled input: text, select, date, time, numeric text, checkbox group | Default · focus · with hint · error · disabled | Native `<input type="date">` and `<input type="time">`. Checkbox groups use `fieldset` + `legend`. Errors start with a visually hidden "Error:". |
| **ErrorSummary** | List of form errors at the top of a form | Hidden · shown (gets focus) | Heading "There is a problem", one link per error that moves focus to the field. |
| **Notice** | Inline message that stays | Info · success · warning (stale data) · error | 4 px left bar in the meaning colour, icon + text. `role="status"` for info and success, `role="alert"` for errors. Never auto-dismissed. |
| **EmptyState** | Says what is empty and what to do | With action · without action | Heading + one sentence + optional action. No illustrations. |
| **ErrorState** | A page or section that couldn't load | Error · retrying | Heading, mapped message, **Retry**, support reference when present. |
| **LoadingState** | First load of a page or section | Loading | Visible text with `role="status"`, plus static placeholder blocks shaped like the content (`aria-hidden`). No spinner and no shimmer. The region is `aria-busy` while loading. |
| **Disclaimer** | Verbatim notice from requirements §3 | Footer · inset (Missed doses page) | Same text in both places. |
| **ConfirmDialog** | Confirms a destructive action | Closed · open · confirming (busy) · error inside the dialog | Native `<dialog>` with `showModal()`. Only for **Stop medication** and **Delete schedule**. The title names the thing, the body names the consequence, and focus starts on **Cancel**. Esc = Cancel. Focus returns to the trigger. (MT-026 checks jsdom's `<dialog>` support before writing tests.) |

That's the whole set for v1. The demo notice and skip link live inside AppShell. No generic wrappers, and no component used only once is split out without a reason.

## 6. Wireframes

Scale: 375 px ≈ 46 characters (1 character ≈ 8 px). 1280 px ≈ 104 characters (1 character ≈ 12 px).

```text
[ Label ]          button (≥ 44 px tall; dose buttons ≥ 48 px)
[[ Label ]]        filled button: primary (blue), or danger (red) where marked
[> Label ]         current page in the navigation
[(@) Due now]      status badge, icon + text. Icons: (o) Clock, (@) BellRing,
                   (!) CircleAlert, (v) CircleCheck, (c) ClockCheck,
                   (-) CircleMinus, (i) Info, (+) Plus, (r) RotateCw
[_______]  [ v ]   text input / select          [ ] [x]  checkbox
| ...              a bar at the left of a field: that field has an error
<h1> <h2> <h3>     heading level (not shown on screen)
(link)             underlined link
------             1 px divider
+------+           bordered card or panel (1 px border, 8 px radius, no shadow)
#######            static loading placeholder (no animation)
```

### 6.1 Today (375 px, every status present)

Synthetic day: Demo Patient A (Africa/Harare), Monday 26 October at 09:10, browser in another timezone.

```text
+--------------------------------------------+
| (i) Demo with synthetic data. Don't enter  |
|     real health information. Data resets   |
|     every night.                           |
+--------------------------------------------+
| MediTrack                           (link) |
| Patient: Demo Patient A                    |
| [ Switch patient  v ]                      |
+--------------------------------------------+
| [>Today         ]  [ Medications   ]       |
| [ Missed doses  ]  [ Daily summary ]       |
+--------------------------------------------+
|                                            |
| Today, Monday 26 October              <h1> |
| Times shown in Africa/Harare time.         |
| 3 of 7 doses recorded ·                    |
| Next: 14:00 Demo Med Alpha                 |
| [ (r) Refresh ]                            |
|                                            |
| Needs attention                       <h2> |
| +----------------------------------------+ |
| | 06:00                     [(!) Missed] | |
| | Demo Med Gamma                    <h3> | |
| | 2 drops                                | |
| | No dose was recorded.                  | |
| |                                        | |
| | [[              Taken               ]] | |
| |                                        | |
| | [              Skipped               ] | |
| +----------------------------------------+ |
| +----------------------------------------+ |
| | 08:30                    [(@) Due now] | |
| | Demo Med Delta Extended Release        | |
| | Capsules                               | |
| | 1 capsule                              | |
| |                                        | |
| | [[              Taken               ]] | |
| |                                        | |
| | [              Skipped               ] | |
| +----------------------------------------+ |
|                                            |
| Later today                           <h2> |
| +----------------------------------------+ |
| | 14:00                   [(o) Upcoming] | |
| | Demo Med Alpha                         | |
| | 500 mg, 1 tablet                       | |
| | With food                              | |
| | You can record this from 13:00.        | |
| +----------------------------------------+ |
| +----------------------------------------+ |
| | 21:00                   [(o) Upcoming] | |
| | Demo Med Beta                          | |
| | 1 tablet                               | |
| | You can record this from 20:00.        | |
| +----------------------------------------+ |
|                                            |
| Done                                  <h2> |
| +----------------------------------------+ |
| | 07:00                 [(c) Taken late] | |
| | Demo Med Alpha                         | |
| | 500 mg, 1 tablet                       | |
| | With food                              | |
| | Taken at 08:20                [ Undo ] | |
| +----------------------------------------+ |
| +----------------------------------------+ |
| | 07:30                      [(v) Taken] | |
| | Demo Med Beta                          | |
| | 1 tablet                               | |
| | Taken at 07:32                [ Undo ] | |
| +----------------------------------------+ |
| +----------------------------------------+ |
| | 09:00                    [(-) Skipped] | |
| | Demo Med Gamma                         | |
| | 2 drops                                | |
| | Skipped at 08:50              [ Undo ] | |
| +----------------------------------------+ |
|                                            |
+--------------------------------------------+
| MediTrack records what you report. It does |
| not give medical advice. Contact your      |
| pharmacist or doctor about missed doses.   |
+--------------------------------------------+
```

### 6.2 Today (1280 px)

```text
+------------------------------------------------------------------------------------------------------+
|                    (i) Demo with synthetic data. Don't enter real health                             |
|                        information. Data resets every night.                                         |
+------------------------------------------------------------------------------------------------------+
|                    MediTrack        Patient: Demo Patient A  [ Switch patient v ]                    |
|                    [>Today ] [ Medications ] [ Missed doses ] [ Daily summary ]                      |
+------------------------------------------------------------------------------------------------------+
|                                                                                                      |
|                    Today, Monday 26 October                                  <h1>                    |
|                    Times shown in Africa/Harare time.                                                |
|                    3 of 7 doses recorded · Next: 14:00 Demo Med Alpha                                |
|                    [ (r) Refresh ]                                                                   |
|                                                                                                      |
|                    Needs attention                                           <h2>                    |
|                    +------------------------------------------------------------+                    |
|                    | 06:00   Demo Med Gamma                        [(!) Missed] |                    |
|                    |         2 drops                                            |                    |
|                    |         No dose was recorded.      [[ Taken ]] [ Skipped ] |                    |
|                    +------------------------------------------------------------+                    |
|                    +------------------------------------------------------------+                    |
|                    | 08:30   Demo Med Delta Extended              [(@) Due now] |                    |
|                    |         Release Capsules                                   |                    |
|                    |         1 capsule                  [[ Taken ]] [ Skipped ] |                    |
|                    +------------------------------------------------------------+                    |
|                                                                                                      |
|                    Later today                                               <h2>                    |
|                    +------------------------------------------------------------+                    |
|                    | 14:00   Demo Med Alpha                      [(o) Upcoming] |                    |
|                    |         500 mg, 1 tablet                                   |                    |
|                    |         With food                                          |                    |
|                    |         You can record this from 13:00.                    |                    |
|                    +------------------------------------------------------------+                    |
|                    +------------------------------------------------------------+                    |
|                    | 21:00   Demo Med Beta                       [(o) Upcoming] |                    |
|                    |         1 tablet                                           |                    |
|                    |         You can record this from 20:00.                    |                    |
|                    +------------------------------------------------------------+                    |
|                                                                                                      |
|                    Done                                                      <h2>                    |
|                    +------------------------------------------------------------+                    |
|                    | 07:00   Demo Med Alpha                    [(c) Taken late] |                    |
|                    |         500 mg, 1 tablet · With food                       |                    |
|                    |         Taken at 08:20                            [ Undo ] |                    |
|                    +------------------------------------------------------------+                    |
|                    +------------------------------------------------------------+                    |
|                    | 07:30   Demo Med Beta                          [(v) Taken] |                    |
|                    |         1 tablet                                           |                    |
|                    |         Taken at 07:32                            [ Undo ] |                    |
|                    +------------------------------------------------------------+                    |
|                    +------------------------------------------------------------+                    |
|                    | 09:00   Demo Med Gamma                       [(-) Skipped] |                    |
|                    |         2 drops                                            |                    |
|                    |         Skipped at 08:50                          [ Undo ] |                    |
|                    +------------------------------------------------------------+                    |
|                                                                                                      |
+------------------------------------------------------------------------------------------------------+
|                    MediTrack records what you report. It does not give medical                       |
|                    advice. Contact your pharmacist or doctor about missed doses.                     |
+------------------------------------------------------------------------------------------------------+
```

### 6.3 Today: loading, empty, error, stale (375 px, main area only)

```text
Loading
+--------------------------------------------+
| Today                                 <h1> |
| Loading today's doses…                     |
| +----------------------------------------+ |
| | #####                                  | |
| | ########################               | |
| | ############                           | |
| +----------------------------------------+ |
| +----------------------------------------+ |
| | #####                                  | |
| | ########################               | |
| | ############                           | |
| +----------------------------------------+ |
+--------------------------------------------+

Empty (Demo Patient B has no medications)
+--------------------------------------------+
| Today, Monday 26 October              <h1> |
| Times shown in America/New York time.      |
|                                            |
| No doses planned for today            <h2> |
| Add a medication with a schedule to plan   |
| doses.                                     |
|                                            |
| [[ Go to medications ]]                    |
+--------------------------------------------+

Error (nothing loaded yet)
+--------------------------------------------+
| Today                                 <h1> |
|                                            |
| +----------------------------------------+ |
| | (!) Couldn't load today's doses   <h2> | |
| | MediTrack is temporarily unavailable.  | |
| | Please try again in a moment.          | |
| |                                        | |
| | Support reference:                     | |
| | 4bf92f3577b34da6a3ce929d0e0e4736       | |
| |                                        | |
| | [[ Retry ]]                            | |
| +----------------------------------------+ |
+--------------------------------------------+

Stale (a refresh failed; earlier data stays on screen)
+--------------------------------------------+
| Today, Monday 26 October              <h1> |
| Times shown in Africa/Harare time.         |
| 3 of 7 doses recorded ·                    |
| Next: 14:00 Demo Med Alpha                 |
|                                            |
| +----------------------------------------+ |
| | (!) Couldn't refresh. Showing          | |
| | information from 09:10.                | |
| +----------------------------------------+ |
| [ (r) Refresh ]                            |
|                                            |
| (cards as last loaded)                     |
+--------------------------------------------+
```

### 6.4 Dose card states (375 px)

```text
Saving (both buttons disabled, nothing moves)
+--------------------------------------------+
| +----------------------------------------+ |
| | 08:30                    [(@) Due now] | |
| | Demo Med Delta Extended Release        | |
| | Capsules                               | |
| | 1 capsule                              | |
| |                                        | |
| | [[       Saving…   (disabled)       ]] | |
| |                                        | |
| | [        Skipped   (disabled)        ] | |
| +----------------------------------------+ |
+--------------------------------------------+

Recorded during this visit (card stays where it was)
+--------------------------------------------+
| +----------------------------------------+ |
| | 08:30                      [(v) Taken] | |
| | Demo Med Delta Extended Release        | |
| | Capsules                               | |
| | 1 capsule                              | |
| | Taken at 09:12                [ Undo ] | |
| +----------------------------------------+ |
+--------------------------------------------+

Not recorded (5xx, network error or timeout)
+--------------------------------------------+
| +----------------------------------------+ |
| | 08:30                    [(@) Due now] | |
| | Demo Med Delta Extended Release        | |
| | Capsules                               | |
| | 1 capsule                              | |
| |                                        | |
| | (!) Not recorded. Something went       | |
| |     wrong. Please try again.           | |
| |     Support reference:                 | |
| |     4bf92f3577b34da6a3ce929d0e0e4736   | |
| |                                        | |
| | [[              Retry               ]] | |
| |                                        | |
| | [               Cancel               ] | |
| +----------------------------------------+ |
+--------------------------------------------+

Recorded, log window now closed (page left open until the next day)
+--------------------------------------------+
| +----------------------------------------+ |
| | 21:00                      [(v) Taken] | |
| | Demo Med Beta                          | |
| | 1 tablet                               | |
| | Taken at 21:05                         | |
| | Undo is no longer available because    | |
| | this dose can't be recorded again.     | |
| +----------------------------------------+ |
+--------------------------------------------+

Already recorded (409 DUPLICATE_DOSE_LOG, after refresh)
+--------------------------------------------+
| +----------------------------------------+ |
| | 08:30                      [(v) Taken] | |
| | Demo Med Delta Extended Release        | |
| | Capsules                               | |
| | 1 capsule                              | |
| | (i) Already recorded.                  | |
| | Taken at 09:11                [ Undo ] | |
| +----------------------------------------+ |
+--------------------------------------------+
```

### 6.5 Patients (375 px)

On `/` the header shows only the app name, with no patient switcher and no nav.

```text
+--------------------------------------------+
| (i) Demo with synthetic data. Don't enter  |
|     real health information. Data resets   |
|     every night.                           |
+--------------------------------------------+
| MediTrack                           (link) |
+--------------------------------------------+
|                                            |
| Patients                              <h1> |
| Choose a patient to see today's doses.     |
|                                            |
| ------------------------------------------ |
| Demo Patient A                      (link) |
| Africa/Harare                              |
| [ Edit ]                                   |
| ------------------------------------------ |
| Demo Patient B                      (link) |
| America/New_York                           |
| [ Edit ]                                   |
| ------------------------------------------ |
|                                            |
| [ (+) Add a patient ]                      |
|                                            |
+--------------------------------------------+
| MediTrack records what you report. It does |
| not give medical advice. Contact your      |
| pharmacist or doctor about missed doses.   |
+--------------------------------------------+
```

Adding a patient, after a failed save:

```text
+--------------------------------------------+
| Add a patient                         <h2> |
|                                            |
| +----------------------------------------+ |
| | There is a problem                <h3> | |
| | Enter a name.                   (link) | |
| +----------------------------------------+ |
|                                            |
| | Name                                     |
| | Shown at the top of every page. Up to    |
| | 80 characters.                           |
| | (!) Enter a name.                        |
| | [____________________________________]   |
|                                            |
| Timezone                                   |
| Dose times follow this timezone. It can't  |
| be changed after doses have been recorded. |
| [ Africa/Harare                       v ]  |
|                                            |
| [[             Save patient             ]] |
|                                            |
| [                 Cancel                 ] |
+--------------------------------------------+
```

Patient switcher, open (on any patient page):

```text
+--------------------------------------------+
| MediTrack                                  |
| Patient: Demo Patient A                    |
| [ Switch patient  ^ ]                      |
| +----------------------------------------+ |
| | Demo Patient A (current)               | |
| | Demo Patient B                  (link) | |
| | All patients                    (link) | |
| +----------------------------------------+ |
+--------------------------------------------+
```

### 6.6 Medications (375 px, main area only)

```text
+--------------------------------------------+
|                                            |
| Medications                           <h1> |
| [ (+) Add a medication ]                   |
|                                            |
| [ ] Show stopped medications               |
|                                            |
| ------------------------------------------ |
| Demo Med Alpha                        <h2> |
| 500 mg, 1 tablet                           |
| With food                                  |
| [ Edit medication ]                        |
|                                            |
| Schedules                             <h3> |
| 07:00 and 14:00                            |
| Every day                                  |
| From 1 October, no end date                |
| Missed after 60 minutes                    |
| This schedule has recorded doses, so only  |
| its end date can change. To change times   |
| or days, use Change schedule.              |
| [ Change schedule ]                        |
| [ Change end date ]                        |
|                                            |
| [ (+) Add a schedule ]                     |
| [ Stop medication ]        (danger, quiet) |
| ------------------------------------------ |
| Demo Med Beta                         <h2> |
| …                                          |
| ------------------------------------------ |
| Demo Med Delta Extended Release            |
| Capsules                              <h2> |
| 1 capsule                                  |
| [ Edit medication ]                        |
|                                            |
| Schedules                             <h3> |
| 08:30                                      |
| Every day                                  |
| From 26 October, no end date               |
| Missed after 60 minutes                    |
| [ Edit schedule ]                          |
| [ Delete schedule ]                        |
|                                            |
| [ (+) Add a schedule ]                     |
| [ Stop medication ]        (danger, quiet) |
| ------------------------------------------ |
| Demo Med Gamma                        <h2> |
| …                                          |
| ------------------------------------------ |
+--------------------------------------------+
```

A stopped medication, shown when "Show stopped medications" is ticked:

```text
+--------------------------------------------+
| Demo Med Epsilon                      <h2> |
| 250 mg, 1 tablet                           |
| Stopped on 12 October                      |
|                                            |
| Schedules                             <h3> |
| 08:00                                      |
| Every day                                  |
| From 1 September to 12 October             |
| (no actions: a stopped medication is       |
|  read-only)                                |
+--------------------------------------------+
```

Add a schedule (an example of disjoint weekdays next to Beta's Monday-to-Friday schedule, AC-34):

```text
+--------------------------------------------+
| Add a schedule for Demo Med Beta      <h2> |
|                                            |
| Times                             <legend> |
| Time 1                                     |
| [ 10:00     ]                              |
| [ (+) Add another time ]                   |
|                                            |
| Days                              <legend> |
| Choose at least one day.                   |
| [ ] Monday                                 |
| [ ] Tuesday                                |
| [ ] Wednesday                              |
| [ ] Thursday                               |
| [ ] Friday                                 |
| [x] Saturday                               |
| [x] Sunday                                 |
|                                            |
| Start date                                 |
| [ 31/10/2026           (date picker) ]     |
|                                            |
| End date (optional)                        |
| Leave empty if the schedule has no end     |
| date.                                      |
| [ dd/mm/yyyy           (date picker) ]     |
|                                            |
| Minutes before a dose counts as missed     |
| From 0 to 240. The default is 60.          |
| [ 60   ]                                   |
|                                            |
| [[            Save schedule             ]] |
|                                            |
| [                 Cancel                 ] |
+--------------------------------------------+
```

Change schedule (the schedule has recorded doses):

```text
+--------------------------------------------+
| Change schedule                       <h2> |
| Demo Med Alpha: 07:00 and 14:00, every     |
| day, from 1 October.                       |
|                                            |
| +----------------------------------------+ |
| | (i) Changes start tomorrow.            | |
| | The current schedule ends on the date  | |
| | you choose, and the new schedule       | |
| | starts the next day. Past records stay | |
| | as they are.                           | |
| +----------------------------------------+ |
|                                            |
| Current schedule ends on                   |
| [ 26/10/2026           (date picker) ]     |
|                                            |
| New schedule                      <legend> |
| Starts on                                  |
| [ 27/10/2026           (date picker) ]     |
|                                            |
| Times, Days, End date and Minutes before   |
| a dose counts as missed follow, as in      |
| Add a schedule, prefilled from the         |
| current schedule.                          |
|                                            |
| [[             Save changes             ]] |
|                                            |
| [                 Cancel                 ] |
+--------------------------------------------+
```

Confirm dialog (Stop medication; Delete schedule uses the same layout):

```text
+--------------------------------------------+
| Stop Demo Med Alpha?                  <h2> |
|                                            |
| Its doses will no longer appear on Today   |
| or count as missed. Past records stay.     |
| This can't be undone. To track it again,   |
| add it as a new medication.                |
|                                            |
| [[           Stop medication            ]] |
|                        ^ danger (red fill) |
| [                 Cancel                 ] |
|            ^ focused when the dialog opens |
+--------------------------------------------+
```

### 6.7 Missed doses (375 px, main area only)

```text
+--------------------------------------------+
|                                            |
| Missed doses                          <h1> |
|                                            |
| +----------------------------------------+ |
| | MediTrack records what you report. It  | |
| | does not give medical advice. Contact  | |
| | your pharmacist or doctor about missed | |
| | doses.                                 | |
| +----------------------------------------+ |
|                                            |
| Dates                             <legend> |
| Up to 31 days.                             |
| From                                       |
| [ 20/10/2026           (date picker) ]     |
| To                                         |
| [ 26/10/2026           (date picker) ]     |
|                                            |
| [ Show missed doses ]                      |
|                                            |
| 2 missed doses from 20 October to 26       |
| October.                                   |
|                                            |
| Monday 26 October                     <h2> |
| +----------------------------------------+ |
| | 06:00                     [(!) Missed] | |
| | Demo Med Gamma                    <h3> | |
| | 2 drops                                | |
| | No dose was recorded.                  | |
| | Can be recorded until 06:00 on Tuesday | |
| | 27 October.                            | |
| |                                        | |
| | [[              Taken               ]] | |
| |                                        | |
| | [              Skipped               ] | |
| +----------------------------------------+ |
|                                            |
| Thursday 22 October                   <h2> |
| +----------------------------------------+ |
| | 21:00                     [(!) Missed] | |
| | Demo Med Beta                          | |
| | 1 tablet                               | |
| | No dose was recorded.                  | |
| | This dose can no longer be recorded.   | |
| +----------------------------------------+ |
|                                            |
+--------------------------------------------+
```

Empty:

```text
+--------------------------------------------+
| Missed doses                          <h1> |
| (disclaimer inset and date range as above) |
|                                            |
| No missed doses from 20 October to         |
| 26 October.                                |
+--------------------------------------------+
```

### 6.8 Daily summary (375 px, main area only)

```text
+--------------------------------------------+
|                                            |
| Daily summary                         <h1> |
|                                            |
| Date                                       |
| [ 26/10/2026           (date picker) ]     |
|                                            |
| [ Show summary ]                           |
|                                            |
| Monday 26 October                     <h2> |
|                                            |
| Adherence                                  |
| 50.0%                                      |
| Doses recorded as taken, out of all doses  |
| taken, skipped or missed.                  |
|                                            |
| +----------------------------------------+ |
| | Doses on Monday 26 October  <caption>  | |
| | -------------------------------------- | |
| | Planned                              7 | |
| | Taken                                2 | |
| |   Of which taken late                1 | |
| | Skipped                              1 | |
| | Missed                               1 | |
| | Upcoming or due now                  3 | |
| +----------------------------------------+ |
|                                            |
+--------------------------------------------+
```

Nothing scored yet (AC-26):

```text
+--------------------------------------------+
| Wednesday 28 October                  <h2> |
|                                            |
| Adherence                                  |
| No doses to score yet                      |
| Adherence is shown once a dose is taken,   |
| skipped or missed.                         |
|                                            |
| (table as above: Planned 7, Upcoming or    |
|  due now 7, every other row 0)             |
+--------------------------------------------+
```

## 7. Copy deck

Final wording. All of it goes into `src/copy.ts` (keys below). The AC-38 safety test reads that file directly, so every string added later is checked automatically. Changes to it need Lead review. `{name}` marks a value filled in at runtime. Apostrophes are straight (`'`) so the demo banner and disclaimer match the spec character for character. Ellipses are the single `…` character.

Words used: dose, medication, schedule, taken, skipped, missed, record. Words never used: seamless, effortless, empower, unlock, elevate, journey, delve, "Great job", exclamation marks, or anything that tells someone what to take or when (see [test-strategy §3.7](../docs/test-strategy.md#37-safety-copy-check)).

### 7.1 Shell and shared

| Key | Text | Notes |
|---|---|---|
| `app.name` | MediTrack | |
| `app.skipLink` | Skip to main content | |
| `app.demoBanner` | Demo with synthetic data. Don't enter real health information. Data resets every night. | FR-13, verbatim |
| `app.demoBannerLabel` | Demo notice | Accessible name of the `role="note"` |
| `app.disclaimer` | MediTrack records what you report. It does not give medical advice. Contact your pharmacist or doctor about missed doses. | Requirements §3, verbatim |
| `app.navLabel` | Patient pages | `nav` label |
| `nav.today` | Today | |
| `nav.medications` | Medications | |
| `nav.missed` | Missed doses | |
| `nav.summary` | Daily summary | |
| `patient.current` | Patient: {name} | |
| `patient.switch` | Switch patient | |
| `patient.switchLoading` | Loading patients… | |
| `patient.switchError` | Couldn't load the patient list. | With Retry |
| `patient.allPatients` | All patients | |
| `doc.title` | {page} – {patient} – MediTrack | Without a patient: {page} – MediTrack |
| `notFound.title` | Page not found | |
| `notFound.body` | Check the address, or go to the list of patients. | |
| `notFound.action` | Go to patients | Also used after a patient `NOT_FOUND` |
| `action.retry` | Retry | |
| `action.retrying` | Retrying… | |
| `action.cancel` | Cancel | |
| `action.saving` | Saving… | |
| `error.supportReference` | Support reference: {traceId} | |
| `error.stale` | Couldn't refresh. Showing information from {time}. | With Retry |
| `form.errorSummaryTitle` | There is a problem | |
| `form.errorPrefix` | Error: | Visually hidden, before each field error |
| `form.optional` | (optional) | Added after optional labels |

### 7.2 Status labels

| Key | Text |
|---|---|
| `status.upcoming` | Upcoming |
| `status.due` | Due now |
| `status.missed` | Missed |
| `status.taken` | Taken |
| `status.takenLate` | Taken late |
| `status.skipped` | Skipped |

### 7.3 API errors

| Key | Text | When |
|---|---|---|
| `error.VALIDATION_ERROR` | Check the details and try again. | Summary fallback only; each `errors[].message` is shown next to its field |
| `error.DUPLICATE_DOSE_LOG` | Already recorded. | Shown as information, then the list refreshes |
| `error.OUTSIDE_LOG_WINDOW` | This dose can't be recorded now. Doses can be recorded from 1 hour before to 24 hours after their time. | |
| `error.DOSE_NOT_PLANNED` | This dose isn't on the schedule. Refresh and try again. | |
| `error.SCHEDULE_HAS_LOGS` | This schedule already has records. You can change its end date, or end it and create a new one. | |
| `error.MEDICATION_INACTIVE` | This medication has been stopped. | |
| `error.PATIENT_HAS_LOGS` | The timezone can't be changed after doses have been recorded. | Next to the Timezone field |
| `error.SCHEDULE_OVERLAP` | This medication already has a schedule on those days. End the current schedule first; the new one can start the next day. | Next to the form (AC-34) |
| `error.SERVICE_UNAVAILABLE` | MediTrack is temporarily unavailable. Please try again in a moment. | With Retry |
| `error.NOT_FOUND` | We couldn't find that. It may have been removed. | |
| `error.INTERNAL_ERROR` | Something went wrong. Please try again. | Also any unknown code |
| `METHOD_NOT_ALLOWED` → `error.INTERNAL_ERROR` | Something went wrong. Please try again. | 405, added to the contract by #47. No copy of its own: the UI never sends an unsupported method, so only a bug can cause it (`prompts/frontend-agent.md`) |
| `error.network` | MediTrack couldn't be reached. Check your internet connection and try again. | No response |
| `error.timeout` | MediTrack is taking too long to respond. Please try again. | Client timeout |
| `dose.notRecorded` | Not recorded. | Put before the message on a dose card, for any failed Taken / Skipped |

### 7.4 Patients

| Key | Text | Notes |
|---|---|---|
| `patients.title` | Patients | h1 |
| `patients.intro` | Choose a patient to see today's doses. | |
| `patients.add` | Add a patient | |
| `patients.edit` | Edit | Accessible name: "Edit {name}" |
| `patients.loading` | Loading patients… | |
| `patients.empty.title` | No patients yet | |
| `patients.empty.body` | Add the first one to start tracking their medications. | |
| `patients.error.title` | Couldn't load patients | |
| `patientForm.addTitle` | Add a patient | |
| `patientForm.editTitle` | Edit {name} | |
| `patientForm.name` | Name | |
| `patientForm.nameHint` | Shown at the top of every page. Up to 80 characters. | |
| `patientForm.timezone` | Timezone | |
| `patientForm.timezoneHint` | Dose times follow this timezone. It can't be changed after doses have been recorded. | |
| `patientForm.save` | Save patient | |
| `patientForm.added` | {name} added. | |
| `patientForm.saved` | Changes to {name} saved. | |
| `patientForm.nameRequired` | Enter a name. | |
| `patientForm.nameTooLong` | Name must be 80 characters or fewer. | |
| `patientForm.timezoneRequired` | Choose a timezone. | |

### 7.5 Today and dose cards

| Key | Text | Notes |
|---|---|---|
| `today.title` | Today, {date} | e.g. "Today, Monday 26 October" |
| `today.titleLoading` | Today | h1 until the date is known |
| `today.timezoneNote` | Times shown in {timezone} time. | Only when it differs from the browser's |
| `today.progress` | {recorded} of {total} doses recorded | "{recorded} of 1 dose recorded" when the total is 1 |
| `today.next` | Next: {time} {medication} | Joined to the progress line with " · " |
| `today.group.attention` | Needs attention | |
| `today.group.later` | Later today | |
| `today.group.done` | Done | |
| `today.group.missed` | Missed | |
| `today.refresh` | Refresh | Refetches and regroups (DD-1) |
| `today.refreshing` | Refreshing… | |
| `today.refreshed` | Doses updated. | Announced politely |
| `today.loading` | Loading today's doses… | |
| `today.empty.title` | No doses planned for today | |
| `today.empty.body` | Add a medication with a schedule to plan doses. | |
| `today.empty.action` | Go to medications | |
| `today.error.title` | Couldn't load today's doses | |
| `dose.taken` | Taken | Button |
| `dose.skipped` | Skipped | Button |
| `dose.context` | , {medication} at {time} | Visually hidden, after the button label |
| `dose.recordFrom` | You can record this from {time}. | |
| `dose.recordUntil` | Can be recorded until {time} on {date}. | Missed doses page |
| `dose.noRecord` | No dose was recorded. | Missed doses (AC-38) |
| `dose.windowClosed` | This dose can no longer be recorded. | |
| `dose.recordedTaken` | Taken at {time} | |
| `dose.recordedSkipped` | Skipped at {time} | |
| `dose.undo` | Undo | Accessible name adds `dose.context` |
| `dose.undoing` | Undoing… | |
| `dose.undone` | Record removed. | Announced politely |
| `dose.undoClosed` | Undo is no longer available because this dose can't be recorded again. | Shown once the log window has closed (DD-2) |

### 7.6 Medications and schedules

| Key | Text | Notes |
|---|---|---|
| `meds.title` | Medications | h1 |
| `meds.add` | Add a medication | |
| `meds.showStopped` | Show stopped medications | Checkbox; sets `include_inactive` |
| `meds.loading` | Loading medications… | |
| `meds.empty.title` | No medications yet | |
| `meds.empty.body` | Add the first one to start a schedule. | |
| `meds.error.title` | Couldn't load medications | |
| `meds.edit` | Edit medication | |
| `meds.stop` | Stop medication | Danger, quiet |
| `meds.stoppedOn` | Stopped on {date} | |
| `meds.stopped` | {medication} stopped. | |
| `meds.schedulesTitle` | Schedules | h3 |
| `meds.noSchedule` | No schedule yet. Add one to plan doses. | |
| `stopConfirm.title` | Stop {medication}? | |
| `stopConfirm.body` | Its doses will no longer appear on Today or count as missed. Past records stay. This can't be undone. To track it again, add it as a new medication. | |
| `stopConfirm.confirm` | Stop medication | |
| `medForm.addTitle` | Add a medication | |
| `medForm.editTitle` | Edit {medication} | |
| `medForm.name` | Name | |
| `medForm.nameHint` | As shown on the box or label. | |
| `medForm.dosage` | Dosage | |
| `medForm.dosageHint` | Shown exactly as you type it, for example 1 tablet. | |
| `medForm.instructions` | Instructions | Label gets `form.optional` |
| `medForm.instructionsHint` | For example, with food. | |
| `medForm.save` | Save medication | |
| `medForm.added` | {medication} added. | |
| `medForm.saved` | Changes saved. | |
| `medForm.nameRequired` | Enter the medication name. | |
| `medForm.nameTooLong` | Name must be 100 characters or fewer. | |
| `medForm.dosageRequired` | Enter the dosage. | |
| `medForm.dosageTooLong` | Dosage must be 100 characters or fewer. | |
| `medForm.instructionsTooLong` | Instructions must be 500 characters or fewer. | |
| `schedule.everyDay` | Every day | All 7 days |
| `schedule.weekdays` | Monday to Friday | Days 1–5 |
| `schedule.weekend` | Saturday and Sunday | Days 6–7 |
| `schedule.from` | From {start}, no end date | |
| `schedule.fromTo` | From {start} to {end} | |
| `schedule.grace` | Missed after {minutes} minutes | "1 minute" when 1 |
| `schedule.hasLogs` | This schedule has recorded doses, so only its end date can change. To change times or days, use Change schedule. | |
| `schedule.add` | Add a schedule | |
| `schedule.edit` | Edit schedule | No recorded doses only |
| `schedule.change` | Change schedule | Recorded doses only |
| `schedule.changeEnd` | Change end date | Recorded doses only |
| `schedule.delete` | Delete schedule | No recorded doses only |
| `scheduleForm.addTitle` | Add a schedule for {medication} | |
| `scheduleForm.editTitle` | Edit schedule | |
| `scheduleForm.times` | Times | Legend |
| `scheduleForm.time` | Time {n} | |
| `scheduleForm.addTime` | Add another time | |
| `scheduleForm.removeTime` | Remove | Accessible name "Remove time {n}"; shown only when there are 2 or more times |
| `scheduleForm.days` | Days | Legend |
| `scheduleForm.daysHint` | Choose at least one day. | |
| `scheduleForm.start` | Start date | |
| `scheduleForm.end` | End date | Label gets `form.optional` |
| `scheduleForm.endHint` | Leave empty if the schedule has no end date. | |
| `scheduleForm.grace` | Minutes before a dose counts as missed | |
| `scheduleForm.graceHint` | From 0 to 240. The default is 60. | |
| `scheduleForm.save` | Save schedule | |
| `scheduleForm.added` | Schedule added. | |
| `scheduleForm.saved` | Changes saved. | |
| `scheduleForm.timeRequired` | Enter a time. | |
| `scheduleForm.timeDuplicate` | Enter each time only once. | |
| `scheduleForm.daysRequired` | Choose at least one day. | |
| `scheduleForm.startRequired` | Enter a start date. | |
| `scheduleForm.endBeforeStart` | The end date must be on or after the start date. | |
| `scheduleForm.graceRange` | Enter a whole number from 0 to 240. | |
| `changeSchedule.title` | Change schedule | |
| `changeSchedule.startsTomorrow` | Changes start tomorrow. | When the new start is the patient's today + 1 |
| `changeSchedule.startsOn` | Changes start on {date}. | Otherwise |
| `changeSchedule.explain` | The current schedule ends on the date you choose, and the new schedule starts the next day. Past records stay as they are. | |
| `changeSchedule.endsOn` | Current schedule ends on | Defaults to the patient's today |
| `changeSchedule.newSchedule` | New schedule | Legend |
| `changeSchedule.startsOnLabel` | Starts on | Defaults to end date + 1 (AC-34) |
| `changeSchedule.save` | Save changes | |
| `changeSchedule.done` | Schedule changed. The new schedule starts on {date}. | |
| `changeSchedule.partial` | The current schedule now ends on {date}, but the new schedule wasn't saved. | Then the mapped error and Retry, which re-sends only the new schedule |
| `changeSchedule.endRequired` | Enter the date the current schedule ends. | |
| `endDate.title` | Change end date | |
| `endDate.label` | End date | |
| `endDate.hint` | It can't be earlier than today or the last recorded dose. | |
| `endDate.saved` | End date changed. | |
| `deleteSchedule.title` | Delete this schedule? | |
| `deleteSchedule.body` | {summary}. It has no recorded doses. This can't be undone. | e.g. "08:30, every day, from 26 October" |
| `deleteSchedule.confirm` | Delete schedule | |
| `deleteSchedule.done` | Schedule deleted. | |

### 7.7 Missed doses

| Key | Text | Notes |
|---|---|---|
| `missed.title` | Missed doses | h1 |
| `missed.range` | Dates | Legend |
| `missed.rangeHint` | Up to 31 days. | |
| `missed.from` | From | |
| `missed.to` | To | |
| `missed.show` | Show missed doses | |
| `missed.count` | {n} missed doses from {from} to {to}. | "1 missed dose…" when 1 |
| `missed.empty` | No missed doses from {from} to {to}. | |
| `missed.emptyDefault` | No missed doses in the last 7 days. | If the patient's today isn't known yet |
| `missed.loading` | Loading missed doses… | |
| `missed.error.title` | Couldn't load missed doses | |
| `missed.fromRequired` | Enter a start date. | |
| `missed.toRequired` | Enter an end date. | |
| `missed.fromAfterTo` | The start date must be on or before the end date. | |
| `missed.tooLong` | Choose a range of 31 days or fewer. | |

### 7.8 Daily summary

| Key | Text | Notes |
|---|---|---|
| `summary.title` | Daily summary | h1 |
| `summary.date` | Date | |
| `summary.show` | Show summary | |
| `summary.adherence` | Adherence | |
| `summary.adherenceExplain` | Doses recorded as taken, out of all doses taken, skipped or missed. | |
| `summary.noScore` | No doses to score yet | AC-26, verbatim |
| `summary.noScoreExplain` | Adherence is shown once a dose is taken, skipped or missed. | |
| `summary.tableCaption` | Doses on {date} | |
| `summary.planned` | Planned | |
| `summary.taken` | Taken | Includes late doses |
| `summary.takenLate` | Of which taken late | |
| `summary.skipped` | Skipped | |
| `summary.missed` | Missed | |
| `summary.pending` | Upcoming or due now | |
| `summary.empty` | No doses planned for {date}. | When `planned` is 0 |
| `summary.loading` | Loading summary… | |
| `summary.error.title` | Couldn't load the summary | |
| `summary.dateRequired` | Enter a date. | |

The percentage is shown with one decimal place, as the API returns it ("50.0%"). It is never coloured or labelled good or bad.

## 8. Decisions

### 8.1 Lead decisions on Phase A (2026-10-26)

| Item | Decision |
|---|---|
| DD-1: cards stay in place | **Approved, clarified.** Background refreshes may update a card's status, but not its position. Cards regroup only on reload, on navigating away and back, or with the visible **Refresh** control ([§4.1](#41-today-grouping-and-order)). |
| DD-2: Undo only while the dose can be recorded again | **Approved.** Undoing after the window closes would turn the dose into a missed dose that can't be fixed. Once Undo is gone, one line explains why ([§4.2](#42-recording-and-undo)). |
| DD-4: missed-dose copy follows AC-38 | **Approved.** The docs win over the prompt. |
| Status colours alike in greyscale | **Accepted**, because label, icon and badge style carry the meaning. Evidence: one greyscale screenshot of Today in the Phase B (MT-025) pull request. |
| Q1: dose notes | **Out of v1.** No note field in the UI. FR-05 notes are API-only in v1; docs follow-up in issue #42. |
| Q2: font | **Device built-in fonts.** No web font. |
| Copy | All strings in `src/copy.ts`; the AC-38 copy-safety test reads that file, so new strings are checked automatically. |
| DD-3, DD-5 to DD-12 | **Approved as written** in the MT-020 pull request (#49) ([§8.2](#82-rules-approved-in-the-mt-020-pull-request)). |

### 8.2 Rules approved in the MT-020 pull request

| # | Decision | Why |
|---|---|---|
| DD-3 | A skipped dose with `late: true` shows **Skipped**, not "Skipped late". | The spec labels only late *taken* doses (AC-15). |
| DD-5 | Today refetches every 60 s and on window focus. A 60 s tick re-checks log windows ([§4.3](#43-keeping-data-fresh)). | Statuses change over time, and only the server may change them. |
| DD-6 | Fixed locale `en-GB`, 24-hour clock, year shown only when it differs from the current one. | Matches the copy ("Monday 26 October") and the `HH:MM` schedule times. Output is deterministic in tests. |
| DD-7 | The patient's today for form defaults comes from the Today query's `date`. | The missed-doses response doesn't return its default range, and the UI may not compute patient dates itself. No contract change needed. |
| DD-8 | Forms open in place, not in modal dialogs or on new routes. ConfirmDialog is used only for Stop medication and Delete schedule. | The routes are fixed by the prompt, and modal forms are hard to use at 200% zoom. |
| DD-9 | The patient switcher is a disclosure of links, not an auto-navigating `<select>`. | WCAG 3.2.2 (no change of context on input). |
| DD-10 | After Taken or Skipped succeeds, focus moves to the result line, not to Undo. | A second Enter press can't undo by accident. |
| DD-11 | A failed recording shows **Retry** + **Cancel** in place of Taken / Skipped. | Keeps one primary action on the card, and satisfies AC-36. |
| DD-12 | No "remember last patient". `/` always shows the patient list. | Less hidden state, and nothing to explain. The prompt allows remembering but doesn't require it. |

## 9. Traceability

| Criterion | Where it's handled |
|---|---|
| AC-02 | Patient form maps 422 `errors[].field = timezone` to the Timezone field ([§4.6](#46-forms)) |
| AC-03, AC-05, AC-06 | Medication and schedule form checks and copy ([§7.6](#76-medications-and-schedules)); fields locked when `has_dose_logs` |
| AC-14 | Recording flow, card shows Taken from the refetched day ([§4.2](#42-recording-and-undo)) |
| AC-20 | Undo flow ([§4.2](#42-recording-and-undo)) |
| AC-21 | Saving state: both buttons disabled, 409 → "Already recorded." ([§6.4](#64-dose-card-states-375-px)) |
| AC-22, AC-23, AC-24 | Missed doses default range, 31-day check, list refreshed after a late record ([§6.7](#67-missed-doses-375-px-main-area-only)) |
| AC-26 | "No doses to score yet" ([§6.8](#68-daily-summary-375-px-main-area-only)) |
| AC-27 | Disclaimer in the AppShell footer on every page |
| AC-28 | Status system (text + icon), 48 px dose buttons, focus ring, axe check per page ([§3](#3-status-system)) |
| AC-34 | Overlap message next to the schedule form; "Starts on" defaults to end date + 1 ([§6.6](#66-medications-375-px-main-area-only)) |
| AC-35 | Date and time formatting rules ([§4.4](#44-dates-and-times)) |
| AC-36 | Not-recorded card state with Retry and support reference ([§6.4](#64-dose-card-states-375-px)) |
| AC-38 | Copy deck in `src/copy.ts`, banned phrases avoided ([§7](#7-copy-deck)) |
| AC-40 | Demo notice with `role="note"` on every page ([§4.7](#47-navigation-and-page-structure)) |
| NFR-01 | Type ≥ 18 px, targets ≥ 44 px, keyboard, zoom ([§2](#2-tokens)) |
| NFR-08 | No optimistic success state ([§1](#1-principles), [§4.2](#42-recording-and-undo)) |
