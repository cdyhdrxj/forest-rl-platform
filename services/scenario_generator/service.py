from __future__ import annotations

import random

from services.scenario_generator.models import GeneratedScenario, GenerationRequest
from services.scenario_generator.registry import GeneratorRegistry
from services.scenario_generator.validation import report_from_messages


class EnvironmentGenerationService:
    def __init__(self, registry: GeneratorRegistry):
        self.registry = registry

    def generate(self, request: GenerationRequest) -> GeneratedScenario:
        seed = int(request.seed if request.seed is not None else random.randint(0, 2_147_483_647))
        family_generator = self.registry.get_family(request.environment_kind)
        scenario = family_generator.generate(request, seed)

        for overlay in self.registry.get_overlays(request.task_kind, request.environment_kind):
            overlay.apply(scenario, request)

        messages: list[str] = []
        for validator in self.registry.get_validators(request.task_kind, request.environment_kind):
            messages.extend(validator.validate(scenario))

        scenario.apply_validation_report(
            report_from_messages(
                messages,
                stage="generator.semantic",
                code_prefix=f"{request.environment_kind.value}_{request.task_kind.value}_semantic",
            )
        )
        scenario.runtime_context.setdefault("seed", seed)
        return scenario
