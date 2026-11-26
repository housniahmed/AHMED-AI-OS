# Release gate
B.8 CI runs 45846482541 and 45846471562 succeeded at c65c9bc.
Comparison main...19492cf: ahead 91, behind 0, merge base 1d184b0dc066274ba3b938fca53e694929e9e1ee.
Open PR chain verified via API: 1,2,3,4,5,6,7,8,9,11,12,13,14,15,16,17,18. PR10 independently targets main and adds test_migrations_rls.py, already present in the stack; exclude pending review.
Migration 006 enforces forward-only transitions and terminal immutability. New runtime-role test pending CI. This does not authenticate a human independently of the trusted runtime, nor prevent forged valid forward transitions or forged audit inserts by compromised credentials.
Proposed consolidation: one aggregate PR targeting main, preserve ancestry using merge commit, review exact head and CI before explicit authorization. Do not squash individual stacked PRs or delete branches before verifying ancestry. After merge rerun main CI and inspect logs. No production activation. Remaining risks documented in B.8.
