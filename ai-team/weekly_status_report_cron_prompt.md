You are running the scheduled Excel Fire Protection weekly status report job.

Audience/delivery:
- Present the final draft report visibly in Slack #open-claw for Justin to review.
- Do not auto-publish to Notion, email, SharePoint, GitHub, or any other external destination.
- If a source is unavailable, proceed and flag it clearly at the top of the draft.

Required first step:
1. Read the weekly-status-report skill before doing any collection. Preferred path: `/home/open-claw/.openclaw/workspace/skills/weekly-status-report/SKILL.md`. If the mounted Cowork workspace path exists, also accept `ai-team/agent-workspace/skills/weekly-status-report/SKILL.md`. Follow the skill's instructions unless this cron prompt is more specific.

Reporting window:
- This job runs Saturday at 1:00 AM America/New_York.
- Compile the report for the Monday–Friday that just completed: Monday 00:00 ET through Friday 23:59:59 ET immediately before the Saturday run.
- If the job is run manually on another day, still infer the most recently completed Monday–Friday workweek unless Justin explicitly supplied a different window.

Source collection order:
Collect from all 8 weekly-report sources in this exact order, continuing past unavailable sources instead of blocking:
1. Google Calendar
2. Quo call transcripts and SMS/messages
3. Microsoft To Do
4. Gmail — justin.miller@predictivelines.com
5. Notion Tasks
6. Notion Meeting Notes
7. Slack
8. GitHub activity

Collection rules:
- Run the Quo pre-flight from the skill first. If Quo auth fails, flag it and continue other sources.
- For Quo, cover both known EFP/Predictive Lines numbers from the skill/local notes.
- Deduplicate across sources; report each substantive event once using the richest source.
- Skip spam, OTP codes, newsletters, bot noise, personal/family items, and routine standing status with no movement.
- Include only delta items from the reporting week.
- If an exact connector/tool is not available in OpenClaw, use an available local CLI/MCP/script equivalent if documented in TOOLS.md or the relevant skill. If no safe equivalent exists, mark that source unavailable and continue.

Synthesis:
Use the report template from the skill:
# Excel Fire Protection — Weekly Status Update
**Week of [Month Day] – [Month Day], [Year]**
Prepared by: Justin Miller

Include only sections with actual content:
- Acquisition & Deal Progress
- Operations & Field Work
- Financial & Accounting
- Technology & Infrastructure
- Business Development
- Administrative & HR
- Key Decisions Made
- Action Items & Follow-Ups
- Next Week Outlook

Output requirements:
- Start with a one-line source coverage note only if something is missing or degraded.
- Then present the draft report in clean Slack-compatible markdown.
- End by saying this is a draft for Justin review and asking what he wants changed.
