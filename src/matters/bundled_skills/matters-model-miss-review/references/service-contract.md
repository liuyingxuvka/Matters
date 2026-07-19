# MatterService model-miss contract

## Input

Submit:

- `expected_behavior`
- `observed_behavior`
- `owner_model_id` and current path id
- exact source/operation/projection revisions
- bounded `failure_class`
- opaque private evidence handle
- current product disposition

## Output

MatterService emits one immutable `development_work_item` containing the
bounded claim, affected owner/model ids, required native validation, focused
regression requirement, and rollback requirement.

## Ownership and hard boundaries

Runtime skills cannot mutate requirements, models, tests, validators, prompts,
skills, or canonical core behavior. Private examples stay under
`MATTERS_HOME`; only opaque handles and non-reconstructable failure classes may
cross into development evidence. A model-miss handoff does not prove the later
repair or release.
