# Six-minute judge walkthrough

1. **Problem:** diversion is relational and temporal, while individual rows can look ordinary.
2. **Overview:** state clearly that all data is synthetic and the split is SHG/member-disjoint.
3. **Clean case:** screen `Applicant_A`; show LOW and measured stage timings.
4. **Fraud pattern:** screen `Applicant_E`; show HIGH, time-expanded return-flow cycle, timeline and neutral explanation. Demonstrate the 15-character flagged-approval override.
5. **Hard cases:** `Applicant_B` is LOW despite one slow internal cycle; `Applicant_I` is REVIEW solely because its history is sparse.
6. **Performance:** say that gradient boosting is the best synthetic benchmark. Explain that the topology MLP ranks well but its validation threshold transfers poorly, causing false positives on the disjoint test.
7. **Compliance:** show per-install HMAC privacy, chained audit verification, consent and human review.
8. **Close:** this runs on Raspberry Pi Desktop OS in an x86 VM. Physical Pi and real-data validation are future work.

Reset only pending demo overlays with `python scripts/reset_demo.py` or the confirmed sidebar action.
