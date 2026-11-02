# Card knowledge levels — Android 0.6.6

Reshuffle replaces the language-direction pill above flashcards. The bottom
row offers Don't Know, Unsure and Know; the active choice is highlighted.
Labels save on the current card without advancing, and may be changed later.
Unlabelled cards count as Don't Know. Existing difficult/new progress maps
to Don't Know, learning maps to Unsure, and known maps to Know. Existing
server enum values and card identities remain compatible.

Deck setup has a Select knowledge level checkbox and a dropdown disabled
until checked. It supports all three levels and combines with selected ranks
for flashcards, audio and list practice. Empty matches show a message. A
session retains its launch selection when a card is relabelled; the next
launch uses the updated labels.

Progress saves in the account-specific SQLite database before returning to
the UI. Uploads run in the background. Pending local values override stale
cloud reads; offline snapshots overlay local progress after restart. Upload
acknowledgements match the uploaded timestamp and review count, so an older
response cannot clear a newer edit. Default-deck metadata is preserved.

Tests cover UI positioning, relabelling, filtering for all three levels,
SQLite reopen, stale refresh and concurrent sync acknowledgements. Physical
device checks remain necessary for final usability verification.
