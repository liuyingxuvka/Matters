"""Single-provider ResearchOperation adapter boundary."""

from matters.analysis.operations import (
    AgentOperationOwner,
    AgentOperationResult,
    AgentRunner,
    AnalysisWorkPackage,
    ResearchProviderStatus,
)


class ResearchOperationRunner:
    """Delegates one work package through the C11 advisory operation owner."""

    def __init__(
        self,
        owner: AgentOperationOwner,
        runner: AgentRunner,
        status: ResearchProviderStatus,
    ) -> None:
        self.owner = owner
        self.runner = runner
        self.status = status

    def run(self, package: AnalysisWorkPackage) -> AgentOperationResult:
        if package.operation_type != "research_operation":
            raise ValueError("ResearchOperationRunner accepts research work only")
        return self.owner.run(
            package,
            runner=self.runner,
            research_status=self.status,
        )


__all__ = ["ResearchOperationRunner"]
