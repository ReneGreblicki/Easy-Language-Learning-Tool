# Offline responsiveness — Android 0.6.7

The 0.6.6 knowledge labels remain. Startup previously awaited the upload outbox,
then fetched the catalog before presenting it. Deck opening made repeated
default-catalog requests and attempted another full download after setup.
Each label also scanned and rewrote downloaded JSON snapshots. These are
confirmed blocking paths; the screenshot alone cannot identify the phone's
underlying server-connectivity failure.

Downloaded decks and the saved catalog now load first, with metadata refresh
and progress upload in the background. The home screen listens for a refreshed
catalog. Pull to refresh explicitly requests the server. Default translations
are checked before reusing a download; changing translations still requires
downloading the new pair. Explicit Download refreshes server content. Personal
deck listings fetch metadata/counts; opening an uncached personal deck fetches
only its cards, with progress embedded and pages of 1,000.

Knowledge labels use one SQLite upsert. Reads overlay the progress table,
including acknowledged labels; snapshot refreshes can update acknowledged
rows only when no newer local edit exists. Deck reads and audio-cache merges
query only the selected deck. Reading the library shares one progress lookup.

HTTP headers and stalled bodies have eight-second deadlines; repository
server reads/uploads have twelve-second deadlines. Uploads stop after one
failure and back off for 30 seconds. Polls do not overlap and pause during
deck activity. Repeated taps cannot launch concurrent deck openings; late
home-route errors do not interrupt the study route.

Regression checks cover a stalled remote catalog, offline cache loading,
acknowledged-label persistence without JSON rewrites, outbox backoff, request
deadlines and existing card filters. No physical-phone latency claim is made.
