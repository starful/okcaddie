# Topic CSV (moved)

Content topics are managed in **okadmin** `data/topic_banks/okcaddie/`.
The Work Hub pipeline sets `TOPIC_QUEUE_*` and `TOPIC_BANK_*` when generating content.

Do not add topic rows in this directory.

## Generation guards (okcaddie scripts)

`script/content_quality.py` blocks re-generation of:

- Guide IDs: `guide_seed_*`, `guide_expand_*`, and the retired off-topic guides
  (souvenirs, insurance, kanto-vs-kansai, etc.)
- Course CSV rows whose slug looks like a cafe (`cafe`, `latte`, `roast`, …)

New course/guide prompts require practical sections (Quick Facts → Booking/Steps → Bottom Line)
and reject the old “elite caddy / masterclass” voice.
