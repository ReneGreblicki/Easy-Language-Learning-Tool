# Multilingual frequency-source notice

The 16-language expansion uses a reproducible weighted consensus rather than treating any
single list as ground truth.

- `wordfreq` 3.1.1 supplies a multilingual usage-frequency baseline where the language is
  supported. Its data contains CC BY-SA 4.0 and separately attributed components; its code is
  Apache-2.0.
- The Wiktionary frequency-list index identifies the OpenSubtitles frequency lists as a
  multilingual resource. The application uses the 2018 FrequencyWords extraction, distributed
  under CC BY-SA 4.0, as native-language conversational evidence.
- `frekwencja/most-common-words-multilingual` is derived from the free English sample published
  by `wordfrequency.info` and machine translation. Its repository states that individual data
  files retain their upstream terms. The application uses those files only as rank-agreement
  evidence: a translated-list entry cannot enter the production corpus unless it also occurs in
  a native-language source.
- Kaikki/Wiktionary remains the lexical enrichment and validation layer under Wiktionary's
  applicable CC BY-SA and GFDL terms. Existing sources and source notices remain in force.

Source URLs and pinned revisions are recorded in
`resources/frequency_data/MULTISOURCE_MANIFEST.json`. The source lists are not copied verbatim
into the repository. The packaged corpus contains a normalized, filtered, ranked derivative with
per-record provenance.

This notice is attribution and engineering documentation, not legal advice.
