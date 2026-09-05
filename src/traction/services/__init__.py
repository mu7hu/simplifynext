"""Teammate service abstractions and working functional stubs."""

from traction.services.intake import (
    IntakeProvider,
    MockIntakeProvider,
    FileIntakeProvider,
    DictIntakeProvider,
    FounderIntakeForm,
    normalize_founder_brief,
    get_intake_provider,
)
from traction.services.profiler import (
    ProfilerService,
    MockProfilerService,
    FileProfilerService,
    DictProfilerService,
    get_profiler_service,
    priors_key,
    default_b2b_saas_seed_priors,
)
from traction.services.execution import (
    ExecutionService,
    SimulatedExecutionService,
    MultiChannelExecutionService,
    DryRunExecutionService,
    ApprovalGuardedExecutionService,
    ChannelExecutionAdapter,
    SimulatorChannelAdapter,
    NullChannelAdapter,
    ExecutionError,
    ExecutionNotApprovedError,
    get_execution_service,
)
from traction.services.measurement import MeasurementService, DefaultMeasurementService
from traction.services.digest import (
    DigestService,
    MarkdownDigestService,
    PlainTextDigestService,
    get_digest_service,
)

__all__ = [
    "IntakeProvider",
    "MockIntakeProvider",
    "FileIntakeProvider",
    "DictIntakeProvider",
    "FounderIntakeForm",
    "normalize_founder_brief",
    "get_intake_provider",
    "ProfilerService",
    "MockProfilerService",
    "FileProfilerService",
    "DictProfilerService",
    "get_profiler_service",
    "priors_key",
    "default_b2b_saas_seed_priors",
    "ExecutionService",
    "SimulatedExecutionService",
    "MultiChannelExecutionService",
    "DryRunExecutionService",
    "ApprovalGuardedExecutionService",
    "ChannelExecutionAdapter",
    "SimulatorChannelAdapter",
    "NullChannelAdapter",
    "ExecutionError",
    "ExecutionNotApprovedError",
    "get_execution_service",
    "MeasurementService",
    "DefaultMeasurementService",
    "DigestService",
    "MarkdownDigestService",
    "PlainTextDigestService",
    "get_digest_service",
]
