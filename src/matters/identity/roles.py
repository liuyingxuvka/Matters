"""Pure role vocabulary."""

MATTER_ROLES = frozenset(
    {"assignee_candidate", "owner", "participant", "requester", "reviewer"}
)

__all__ = ["MATTER_ROLES"]
