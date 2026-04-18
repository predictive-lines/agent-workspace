# Interview-invite email template

Short, warm, specific. One concrete hook per email. Under ~160 words.

## Subject

`Excel Fire Protection — quick intro call?`

## Body (HTML)

```html
<p>Hi {first_name},</p>
<p>
  I'm Justin Miller, GM / owner at Excel Fire Protection in Marquette, MI. Thanks for putting
  your application in for our Journeyman Sprinkler Fitter position — {one_specific_hook}.
</p>
<p>
  I'd love to set up a short intro call (~20–30 minutes) to walk through the role, the crew,
  and what you're looking for. Would any of these windows work for you
  {next_monday_long_form}?
</p>
<ul>
  <li>9:00–9:30 AM ET</li>
  <li>11:00–11:30 AM ET</li>
  <li>2:00–2:30 PM ET</li>
</ul>
<p>
  If none of those land, just reply back with two or three windows that work for you and I'll
  make one of them fit.
</p>
<p>Thanks —<br>
Justin Miller<br>
Excel Fire Protection</p>
```

## Placeholder rules

- `{first_name}` — first name from the Screen dialog. Trim titles/suffixes.
- `{one_specific_hook}` — exactly one clause referencing something concrete from the
  candidate's background. Examples:
  - `your time leading the FP department at Pro Shield Fire stood out`
  - `a 5/5 on troubleshooting and servicing sprinkler systems is the profile we're short on right now`
  - `we don't see many applicants coming in from Eustis, FL — curious to hear what's drawing you north`
  Never stack multiple hooks. One is warm; three is a LinkedIn recruiter.
- `{next_monday_long_form}` — the next upcoming Monday as `"on Monday, April 27"` style. If
  today *is* Monday, use the Monday one week out.

## Tone guardrails

- No "I hope this email finds you well."
- No bullet list of job requirements.
- No compensation talk.
- No "we are excited" / "we are thrilled" boilerplate.
- End with Justin's name, not "best regards" or "kind regards".
- `Excel Fire Protection` on its own line under the name — no phone/address footer, Outlook
  will append Justin's signature where configured.

## Edge cases

- No email on file in the Screen dialog → skip the draft, report the candidate in the summary
  with `email: missing`.
- Email present but looks malformed (no `@`, whitespace, etc.) → skip the draft, flag it.
- Out-of-state candidate (not MI / not a commutable Marquette-area address) → still draft, but
  the hook should acknowledge relocation naturally (e.g. "curious what's drawing you to the UP").
