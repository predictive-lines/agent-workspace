Subject: Quo API request: expose MMS/media attachments on message endpoints and webhooks

Hi Quo team,

We’re integrating the Quo API into an internal MCP workflow and found that inbound MMS media is not currently exposed through the public message surfaces.

What we tested
- `GET /v1/messages?phoneNumberId=...&participants=...`
- `GET /v1/messages/{id}`
- message webhook docs / payload examples

What we observed
- Message objects currently expose fields like:
  - `id`
  - `from`
  - `to`
  - `text`
  - `phoneNumberId`
  - `direction`
  - `userId`
  - `status`
  - `createdAt`, `updatedAt`
- For an inbound MMS that definitely included a photo, the API response still only returned the text body, with no media metadata.
- The published docs for `List messages`, `Get a message by ID`, and the sample `message.received` webhook payload appear to match this limitation.

Why this matters
A lot of automation use cases depend on being able to detect and retrieve media from messages, for example:
- AI/agent workflows that inspect inbound photos
- CRM/work-order intake from field photos
- message triage where attachments change the meaning of the thread
- archiving/compliance workflows

Requested enhancement
Please expose MMS/media on message resources and webhooks.

At minimum, it would help to have a field like `attachments` or `media` on message objects, with entries such as:
- `id`
- `type` or `mimeType`
- `filename` (if available)
- `size` (if available)
- `url` or signed download URL
- optional thumbnail URL for images/videos

Ideal surfaces
- `GET /v1/messages`
- `GET /v1/messages/{id}`
- message-related webhooks, especially `message.received`

Nice to know
- If this functionality already exists in a private/beta endpoint, we’d love to use it.
- If there is a roadmap or ETA for MMS/media support in the API, that would be very helpful.

Thanks, this would unlock a bunch of really useful workflows for us.
