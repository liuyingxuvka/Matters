"""Pure invalidation inventory helpers."""

from matters.revisions.corrections import DependentDisposition


def undisposed(
    expected_ids: tuple[str, ...],
    dispositions: tuple[DependentDisposition, ...],
) -> tuple[str, ...]:
    observed = {item.dependent_id for item in dispositions}
    return tuple(item for item in expected_ids if item not in observed)


__all__ = ["undisposed"]
