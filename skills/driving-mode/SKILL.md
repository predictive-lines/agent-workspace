---
name: driving-mode
description: |
  Handle driving-mode behavior. In `#driving-mode`, thread context now
  implies driving mode for conversation/TTS. The persistent flag remains
  only for Signal-message auto-forwarding. Also handles explicit requests
  to turn Signal forwarding on/off.
---

# Driving mode behavior

Driving mode is now split into **two separate concepts**:

1. **Conversation driving mode** in Slack is determined by **channel/thread
   context**, not a global flag.
2. **Signal forwarding driving mode** is still controlled by the persistent
   flag at `/home/open-claw/.openclaw/state/driving_mode`.

## 1) Conversation behavior in Slack

Inside `#driving-mode`, treat the conversation as driving mode by default.
That means:

- In **threads inside `#driving-mode`**, assume Justin is driving.
- Use the `tts` tool for substantive replies in that context.
- Outside `#driving-mode`, stay text-only unless Justin explicitly asks for
  audio for some other reason.

Do **not** require Justin to say "driving mode on" just to get driving-mode
conversation behavior inside that channel.

## 2) Signal forwarding flag

The file `/home/open-claw/.openclaw/state/driving_mode` now exists only to
control whether incoming Signal messages from Jaclyn are auto-forwarded into
Slack `#driving-mode` for iOS Announce Notifications.

### Flag semantics

- **Empty file / content does not start with `on`** → Signal forwarding OFF
- **Content starts with `on`** (e.g. `on` or `on 2026-04-19T18:30:00Z`) → Signal forwarding ON

## How to interpret requests

### Requests about conversation behavior

If Justin is talking in `#driving-mode`, just behave as though driving mode is
active for that thread. No flag write needed.

### Requests like "turn on driving mode" / "I'm driving"

Interpret these as requests to enable **Signal forwarding**, unless context
clearly says he means something else.

1. Write `on <current ISO timestamp>` to `/home/open-claw/.openclaw/state/driving_mode`
2. Confirm briefly that Signal forwarding is on
3. Continue treating `#driving-mode` conversations as driving-mode contexts
   because of the channel, not because of the flag

### Requests like "driving mode off" / "I'm done driving" / "stop driving mode"

Interpret these as requests to disable **Signal forwarding**.

1. Truncate `/home/open-claw/.openclaw/state/driving_mode` to empty
2. Confirm briefly that Signal forwarding is off
3. Do **not** imply that `#driving-mode` threads stop being driving-mode
   conversations. The channel semantics remain the same.

## Don't

- Don't confuse conversation driving mode with the Signal forwarding flag.
- Don't require a global toggle for normal conversation inside `#driving-mode`.
- Don't write the flag unless Justin explicitly asks to control Signal-side
  forwarding.
- Don't confuse "driving mode" with literal driving directions or vehicle
  advice.
