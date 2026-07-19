# Matters FlowGuard ModelMesh

This is a human-readable projection of the executable hierarchy in
`flowguard_models/model_mesh.py`. It does not replace the native FlowGuard
receipt.

```mermaid
flowchart TD
    M0["M0 End-to-End Authority"]
    C1["C1 Authorization & Coverage"]
    C2["C2 Source Registry"]
    C3["C3 Evidence Qualification"]
    C4["C4 Person & Entity Resolution"]
    C5["C5 Event & Temporal Trace"]
    C6["C6 Matter Formation & Admission"]
    C7["C7 Lifecycle & Board State"]
    C8["C8 Open Loop / Waiting / Blocking"]
    C9["C9 Completion / Cancellation / Reopen"]
    C10["C10 Correction / Revocation"]
    C11["C11 Guard Artifact & Prediction"]
    C12["C12 Projection & Bilingual UI"]

    M0 --> C1
    C1 -->|AuthorizedBatch| C2
    C2 -->|SourceVersion| C3
    C2 -->|SourceVersion| C11
    C3 -->|EvidenceAnchor / AssertionCandidate| C4
    C3 -->|EvidenceAnchor / AssertionCandidate| C5
    C4 --> C6
    C5 --> C6
    C6 -->|AdmittedMatter| C7
    C6 -->|AdmittedMatter| C8
    C7 --> C9
    C8 --> C9
    C7 --> C12
    C8 --> C12
    C9 --> C12
    C11 -.advisory only.-> C3
    C11 -.advisory only.-> C5
    C11 -.advisory only.-> C7
    C10 -.invalidate and request original owner recompute.-> C2
    C10 -.-> C3
    C10 -.-> C4
    C10 -.-> C5
    C10 -.-> C6
    C10 -.-> C7
    C10 -.-> C8
    C10 -.-> C9
```

M0 owns only orchestration receipt state. Each child owns exactly its declared
canonical fields and side effects. Every output token is producer-qualified in
the executable mesh, so identical display labels from different children
cannot conceal an unconsumed producer.

`mesh_green` is bounded to model partition, abstract and known-bad evidence,
current evidence reattachment, output consumption, join reachability, and
terminal closure. It is not production, live-provider, conformance, or UI
runtime evidence.

All G3 evidence is generated and consumed inside one local Python process.
There is therefore no process boundary requiring a portable-model refinement
binding at this gate. Any later subprocess, plugin, or external verifier
boundary must add and validate a portable artifact before its evidence can be
consumed.
