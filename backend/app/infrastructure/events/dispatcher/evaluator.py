from app.core.exceptions.infrastructure import InfrastructureError
from app.domain.events.enum import DispatchTarget
from app.domain.events.schema import Event


class DispatchEvaluator:
    def __init__(self, critical_targets: set[DispatchTarget]):
        self.critical_targets = critical_targets

    def evaluate(
        self,
        event: Event,
        results: dict[DispatchTarget, bool],
        errors: list[tuple[DispatchTarget, str]],
    ):
        """
        בודק האם התוצאות עומדות במדיניות הקריטיות של המערכת.
        """
        failures = [t for t, success in results.items() if not success]
        critical_failures = [t for t in failures if t in self.critical_targets]

        if critical_failures:
            raise InfrastructureError(
                message=f"Critical dispatch failure for {event.name}",
                detail=f"Failed critical targets: {critical_failures}. Full errors: {errors}",
            )

        return failures  # מחזיר רשימת כשלים לא קריטיים למעקב
