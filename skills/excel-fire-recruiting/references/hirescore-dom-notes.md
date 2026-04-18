# HireScore DOM notes

Captured 2026-04-18 against cycle 7239 ("Journeyman Sprinkler Fitter") using the OpenClaw
`chromium-user` browser profile and `refs: "aria"` snapshots. Read this when selectors drift
or HireScore ships a redesign.

## Auth detection

On `/cycles/<id>/detail`:

- Logged-in sentinel: `role: button, name: "Justin Miller"` in the top-right user area.
- Logged-out behavior: URL redirects to `/login?next=/cycles/<id>/detail` and the page shows
  email/password inputs and a `Sign In` button. Cookie banner appears once per fresh profile.

## Cycle list view

Columns, in order: `Name`, `Apply Date`, `Online Application`, `BVI`, `BASELINE`, `Notes`,
`Tag`, `Status`.

Per-row snapshot pattern (one candidate = one cluster of `statictext`/`link` nodes):

```
statictext "<Full Name>"       # clicking this opens the Screen dialog
statictext "<City, ST>"
statictext "MM/DD/YYYY"        # apply date
link "<nn>"                    # Online Application percentile (nested statictext has same value)
link "<nn>"                    # BVI percentile
statictext "<nn>"              # Baseline percentile
button "Pending" | "<label>"   # Status
```

There is a `checkbox "Select applicant"` immediately before each row — use it to distinguish
one row from the next when iterating.

## Screen dialog

Clicking the candidate name opens a `role: dialog` modal. The dialog's `description`
attribute is a single flattened string containing the entire rendered profile, in this order:

```
Download as PDF SCREEN WITH <position> <apply_date>
<full name>
<street address>
<city state zip>
<email>
<phone digits>
EDUCATION
Highest Level of Education: <level>
[repeating: <school> <program> <year|N/A> <gpa|N/A>]
EXPERIENCE
[repeating: <title> <company> <city_or_zip> Employed: <range> Salary: <range> Description of work: <text>]
No expertise 1 - Expert 5
EXPERTISE
[repeating: <skill prompt> <1-5>]
POSITION: <position>
SUBMITTED: <mm/dd/yyyy>
```

The same fields also appear as individual child `role: statictext` nodes. These are the
authoritative source — the `description` attribute is frequently truncated for longer
candidate profiles (observed on cycle 7239, Dion Davis: description cut off mid-expertise
block). When you need the full text, walk the dialog's child nodes in order using the
section markers (`EDUCATION`, `EXPERIENCE`, `EXPERTISE`, `POSITION:`, `SUBMITTED:`) as
delimiters. `scripts/parse_screen_dialog.py` accepts either form — pass it the description
attribute when short, or pass the concatenated statictext children joined with spaces.

Close the dialog with `Escape` (confirmed working). Alternate: the dialog's first `role:
button` with empty `name` is the "X" close control.

## Known footguns

- The cycle table is virtualized — when a cycle has more rows than the viewport, scroll and
  re-snapshot instead of trusting a single snapshot to list everything. For cycle 7239 (2
  rows) this isn't needed.
- The `Online Application` / `BVI` columns render as *links*, not plain text, and clicking
  them drills into a sub-report. Read them from the link's `name`, don't click them.
- A single `iframe` node appears at the end of the snapshot (looks like a tracking/analytics
  embed). Ignore it; content lives in the main rootwebarea.
- The top-right user button (`role: button, name: "<Full Name>"`) is the *logged-in* account,
  not a candidate — don't treat it as a row.
