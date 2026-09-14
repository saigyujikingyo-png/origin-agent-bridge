"""Strict, compatibility-preserving contracts for server-produced tool results.

These models validate existing dictionaries; callers must not serialize the models
back over legacy responses. Optional defaults describe omitted fields without
inventing a measurement, check, artifact, or lifecycle transition. Arbitrary JSON
is reserved for documented extension points and is bounded by the delivery layer.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

Identifier = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ArtifactId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}/[^/\\]+$")]
Count = Annotated[int, Field(ge=0)]
Seconds = Annotated[float, Field(ge=0)]
CapabilityKind = Literal["xfunction", "fitting", "template", "api", "documentation"]
SessionState = Literal["opening", "executing", "ready", "gui", "suspended", "closed", "needs_attention"]


def _strict_bool(value):
    # Pydantic Literal[True/False] alone also matches 1/0, even in strict mode.
    if type(value) is not bool:
        raise ValueError("Boolean evidence must be a JSON boolean")
    return value


TrueFlag = Annotated[Literal[True], BeforeValidator(_strict_bool)]
FalseFlag = Annotated[Literal[False], BeforeValidator(_strict_bool)]


class OutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class ValidationIssue(OutputModel):
    field: str
    message: str
    type: str


class ErrorOutput(OutputModel):
    error: Literal["validation", "syntax", "invalid_request", "tool", "execution", "output_validation"]
    message: str | None = None
    issues: list[ValidationIssue] | None = Field(default=None, max_length=6)
    line: int | None = None
    column: int | None = None
    recovery: JsonObject | None = None
    operation: str | None = None
    job_id: Identifier | None = None
    plan_id: Identifier | None = None
    dataset_id: Identifier | None = None
    session_id: Identifier | None = None

    @model_validator(mode="after")
    def error_details(self):
        if self.error == "validation" and not self.issues:
            raise ValueError("Validation errors must identify at least one issue")
        if self.error != "validation" and self.message is None:
            raise ValueError("A non-validation error requires its message")
        return self


class Engine(OutputModel):
    version: float
    bitness: int
    edition: Literal["Origin", "OriginPro"]
    demo: int
    executable_directory: str
    originpro: str | None = None
    OriginExt: str | None = None


class Baseline(OutputModel):
    id: str
    label: str
    version: float
    native_acceptance: Literal["pending", "documented_cases_passed"]


class TargetProfile(OutputModel):
    id: str
    label: str
    baselines: list[Baseline]
    bitness: int
    edition: str
    distribution: str
    full_functionality_verified: bool


class TargetAssessment(OutputModel):
    status: Literal["not_probed", "match", "mismatch"]
    target: TargetProfile
    matched_baseline: Baseline | None
    scope: str
    reasons: list[str] | None = None

    @model_validator(mode="after")
    def matching_evidence(self):
        if (self.status == "match") != (self.matched_baseline is not None):
            raise ValueError("A matched baseline is present only after a matching native assessment")
        if self.status == "mismatch" and not self.reasons:
            raise ValueError("A mismatch requires its reasons")
        return self


class BenchmarkPreference(OutputModel):
    model: str
    effort: str
    required: bool


class ProfileReport(OutputModel):
    preset: Literal["generic", "deepseek", "gpt-terra", "gemini", "glm", "kimi", "elm"]
    mode: Literal["full", "economy"]
    vision: Literal["auto", "off", "on"]
    schema_version: Literal[1]
    host_requirement: str
    host_recommendation: str
    benchmark_preference: BenchmarkPreference
    model_selected_by: str
    model_quality_verified: bool


class Device(OutputModel):
    computer_name: str
    scope: str


class Dependencies(OutputModel):
    originpro: str | None
    OriginExt: str | None


class ProgramEnvironment(OutputModel):
    python: str
    excluded_from_release: list[str]
    preferred_table_route: str
    api_discovery: str


class StatusLimits(OutputModel):
    input_mib: Count
    rows: Count
    columns: Count
    panels_per_job: Count


class OutputContractDescriptor(OutputModel):
    version: Literal["1.0.0"]
    server_validation: TrueFlag
    schema_discovery: str


class StatusOutput(OutputModel):
    plugin_version: str
    product_name: str
    agent_profile: ProfileReport
    device: Device
    platform: str
    architecture: str
    installations: list[str]
    configured_executable: str | None
    dependencies: Dependencies
    target_profile: TargetProfile
    native_ready_to_probe: bool
    connection_policy: str
    last_native_engine: Engine | None
    last_native_target_assessment: TargetAssessment
    data_directories: list[str]
    inbox: str
    compute: str
    program_environment: ProgramEnvironment
    capabilities: list[str]
    limits: StatusLimits
    output_contract: OutputContractDescriptor


class ColumnQuality(OutputModel):
    name: str
    numeric: Count
    missing: Count
    other: Count
    min: float | None
    max: float | None


class DatasetOutput(OutputModel):
    dataset_id: Identifier
    name: str
    sha256: Sha256
    snapshot: Literal["local immutable snapshot"]
    sheet_name: str | None
    bytes: Count
    row_count: Annotated[int, Field(ge=1, le=250000)]
    columns: list[ColumnQuality] = Field(min_length=2, max_length=128)
    preview: list[Annotated[list[str], Field(max_length=12)]] = Field(max_length=4)
    preview_columns: list[str] = Field(max_length=12)


class CapabilityEntry(OutputModel):
    id: str
    kind: CapabilityKind
    name: str
    category: str
    signature: str | None = None
    help: str | None = None
    reference: str | None = None
    local_path: str | None = None
    help_command: str | None = None
    usage: str | None = None


class CapabilityContext(OutputModel):
    installation: str
    counts: dict[CapabilityKind, Count]
    availability: str
    execution: str
    gui_only: str


class CapabilitySearchOutput(CapabilityContext):
    total_matches: Count
    offset: Count
    next_offset: Count | None
    entries: list[CapabilityEntry] = Field(max_length=30)


class CapabilityDetailOutput(CapabilityContext):
    entry: CapabilityEntry


class CoverageCategory(OutputModel):
    name: str
    verified_examples: list[str]
    remaining: str


class CoverageOutput(OutputModel):
    baseline: str
    version: str
    full_functionality_verified: bool
    meaning: str
    routes: list[str]
    categories: list[CoverageCategory]
    evidence_scripts: list[str]
    limits: list[str]


class AnalysisSpec(OutputModel):
    kind: Literal["linear_fit", "beer_lambert"]
    intercept: Literal["free", "zero"]
    weighting: Literal["none"]
    unknown_absorbance: float | None
    path_length_cm: float | None
    concentration_scale_molar: float | None


class StyleSpec(OutputModel):
    preset: Literal["report", "presentation"]
    x_label: str | None
    y_label: str | None
    width: int
    plot: Literal["scatter", "line", "line_symbol"]
    x_tick_format: Literal["auto", "decimal", "scientific"] | None = None
    y_tick_format: Literal["auto", "decimal", "scientific"] | None = None
    colors: list[str]


class PanelSpec(OutputModel):
    dataset_id: Identifier
    x: str
    y: list[str]
    y_errors: dict[str, str]
    title: str
    analysis: AnalysisSpec | None
    style: StyleSpec


class WorkflowSpec(OutputModel):
    revision: str | None
    panels: list[PanelSpec] = Field(min_length=1, max_length=12)
    formats: list[Literal["png", "pdf", "svg"]]
    timeout_seconds: int


class PlanPanelSummary(OutputModel):
    title: str
    rows: Count
    x: str
    y: list[str]
    analysis: AnalysisSpec | None
    error_bars: dict[str, str]
    style: StyleSpec


class PlanOutput(OutputModel):
    plan_id: Identifier
    sha256: Sha256
    summary: list[PlanPanelSummary] = Field(min_length=1, max_length=12)
    outputs: list[str]
    assumptions: list[str]
    native_execution: FalseFlag


class UnknownUncertainty(OutputModel):
    status: Literal["not_calculated"]
    value: None
    reason: Literal["inverse_calibration_uncertainty_not_supported"]
    method: None


class FitSummary(OutputModel):
    panel: Annotated[int, Field(ge=1, le=12)]
    series: str
    n: Count
    slope: float
    intercept: float
    slope_se: Annotated[float, Field(ge=0)]
    r_squared_origin: float
    residual_sum_squares: Annotated[float, Field(ge=0)]
    intercept_mode: Literal["free", "zero"]
    weighting: Literal["none"]
    coefficient_rss_crosscheck: TrueFlag
    unknown_concentration_in_x_units: float | None = None
    extrapolation: bool | None = None
    unknown_uncertainty: str | None = None
    unknown_uncertainty_result: UnknownUncertainty | None = None
    molar_absorptivity_L_mol_cm: float | None = None


class PlotSummary(OutputModel):
    panels: Count
    analysis: Literal["plot only"]


class ProgramSummary(OutputModel):
    title: str
    language: Literal["python", "labtalk", "origin_c"]
    results_artifact: ArtifactId
    graphs: Count


class SessionSummary(OutputModel):
    title: str
    action: Literal["open", "execute", "checkpoint", "restore", "close"]
    session_id: Identifier
    revision: Count
    results_artifact: ArtifactId | None


class GuiSummary(OutputModel):
    action: Literal[
        "gui_begin",
        "gui_observe",
        "gui_invoke",
        "gui_set_text",
        "gui_dismiss",
        "gui_select",
        "gui_toggle",
        "gui_expand",
        "gui_collapse",
        "gui_click",
        "gui_drag",
        "gui_keys",
        "gui_type_text",
        "gui_scroll",
        "gui_commit",
        "gui_rollback",
    ]
    session_id: Identifier
    revision: Count


type JobSummary = FitSummary | PlotSummary | ProgramSummary | SessionSummary | GuiSummary
TickProperties = dict[
    Literal["x.label.numFormat", "y.label.numFormat", "x.label.decPlaces", "y.label.decPlaces"], int
]


class AxisTickFormat(OutputModel):
    graph: str
    properties: TickProperties


class WorkflowVerification(OutputModel):
    vendor_native: TrueFlag
    project_reopened: TrueFlag
    data_roundtrip: TrueFlag
    graphs_reopened: Count
    graph_text_roundtrip: bool | None = None
    axis_tick_format_roundtrip: bool | None = None
    axis_tick_formats: list[AxisTickFormat] | None = None
    titles_reopened: Count | None = None
    native_reports_reopened: Count
    png_decoded: bool
    visual_review: str
    seconds: Seconds


class ProgramVerification(OutputModel):
    vendor_native: TrueFlag
    project_reopened: bool
    structure_roundtrip: bool
    live_session_preserved: bool
    numeric_data_roundtrip: FalseFlag
    independent_scientific_validation: FalseFlag
    explicit_postconditions_passed: Count
    pngs_decoded: Count
    visual_review: str
    seconds: Seconds


class SessionVerification(OutputModel):
    vendor_native: TrueFlag
    project_saved: bool
    project_reopened: FalseFlag
    independent_scientific_validation: FalseFlag
    seconds: Seconds


class GuiVerification(OutputModel):
    vendor_native: TrueFlag
    gui_observed: bool
    screenshot_captured: bool
    project_saved: bool
    project_reopened: bool
    gui_semantic_success: str
    independent_scientific_validation: FalseFlag
    seconds: Seconds


type Verification = WorkflowVerification | ProgramVerification | SessionVerification | GuiVerification


class DataReference(OutputModel):
    sheet: str
    columns: Count
    rows: Count
    sha256: Sha256


class FitReference(OutputModel):
    report: str
    curve: str


class GraphTextReference(OutputModel):
    graph: str
    labels: dict[str, str]
    tick_properties: TickProperties | None = None


class WorkflowProjectIndex(OutputModel):
    data: list[DataReference]
    graphs: list[str]
    fits: list[FitReference]
    graph_text: list[GraphTextReference] | None = None


class ProjectSheet(OutputModel):
    name: str
    rows: Count
    columns: Count
    matrices: Count | None = None


class ProjectPage(OutputModel):
    name: str
    long_name: str
    type: str
    sheets: list[ProjectSheet] | None = None
    sheet_count: Count | None = None


class SnapshotProjectIndex(OutputModel):
    pages: list[ProjectPage]
    graphs: list[str]


class PublicProjectIndex(SnapshotProjectIndex):
    page_count: Count
    graph_count: Count
    truncated: bool


type ProjectIndex = WorkflowProjectIndex | SnapshotProjectIndex | PublicProjectIndex


class SessionReceipt(OutputModel):
    session_id: Identifier
    revision: Count
    state: SessionState
    checkpoint_id: Identifier


class SessionInspectOutput(OutputModel):
    session_id: Identifier
    title: str
    revision: Count
    visible: bool
    state: SessionState
    gui_transaction_open: bool
    active_job: Identifier | None = None
    last_job: Identifier | None = None
    last_failure: Identifier | None = None
    checkpoint_id: Identifier | None = None
    checkpoint_sha256: Sha256 | None = None
    recovery_sha256: Sha256 | None = None
    project_index: PublicProjectIndex | SnapshotProjectIndex | None = None
    origin_pid: int | None = None
    updated: float | None = None
    gui_observation_id: Identifier | None = None


class GuiWindow(OutputModel):
    id: str
    class_name: str = Field(alias="class")
    text: str
    enabled: bool
    rect: list[int] = Field(min_length=4, max_length=4)
    popup: bool


class MenuTarget(OutputModel):
    id: str
    kind: Literal["menu"]
    text: str
    enabled: bool


class ControlTarget(GuiWindow):
    kind: Literal["control"]
    window_id: str
    control_id: int


class AccessibleTarget(OutputModel):
    id: str
    kind: Literal["accessible"]
    text: str
    class_name: str = Field(alias="class")
    role: int
    automation_id: str
    window_id: str
    enabled: bool
    rect: list[int] = Field(min_length=4, max_length=4)
    actions: list[str]
    # UIA providers expose these property variants; the producer accepts any JSON scalar.
    value: str | bool | int | float | None = None
    selected: str | bool | int | float | None = None
    toggle_state: str | bool | int | float | None = None
    expanded_state: str | bool | int | float | None = None


class GuiCapture(OutputModel):
    window_id: str
    rect: list[int] = Field(min_length=4, max_length=4)
    width: Count
    height: Count
    client_rect: list[int] = Field(min_length=4, max_length=4)
    coordinate_system: str


class GuiObservation(OutputModel):
    observed_at: float
    blocked: bool
    truncated: bool
    query: str
    backend: Literal["win32+uia"]
    windows: list[GuiWindow] = Field(max_length=32)
    targets: list[MenuTarget | ControlTarget | AccessibleTarget] = Field(max_length=160)
    observation_id: Identifier
    capture: GuiCapture | None = None
    screenshot_window_id: str | None = None
    screenshot_artifact_id: ArtifactId | None = None
    screenshot_error: str | None = None


class ArtifactRow(OutputModel):
    artifact_id: ArtifactId
    name: str
    bytes: Count
    sha256: Sha256
    mime_type: str


class JobProgress(OutputModel):
    stage: str
    elapsed_seconds: Seconds | None = None
    kind: Literal["program"] | None = None
    completed_panels: Count | None = None
    total_panels: Count | None = None
    last_stage: str | None = None


class JobBase(OutputModel):
    job_id: Identifier
    plan_id: Identifier
    error: str | None
    cancel_requested: bool
    elapsed_seconds: Seconds
    progress: JobProgress | None = None
    session_id: Identifier | None = None
    assumptions: list[str] | None = None


class PendingJob(JobBase):
    state: Literal["queued", "running"]
    terminal: FalseFlag
    poll_after_seconds: Count


class JobDiagnostic(OutputModel):
    type: str | None
    labtalk_output: str = Field(max_length=4000)


class JobRecovery(OutputModel):
    kind: Literal["missing_python_dependency", "unknown_native_api"]
    instruction: str


class UnsuccessfulJob(JobBase):
    state: Literal["failed", "cancelled", "interrupted"]
    terminal: TrueFlag
    next_action: str
    diagnostic: JobDiagnostic | None = None
    recovery: JobRecovery | None = None


class SucceededJob(JobBase):
    state: Literal["succeeded"]
    terminal: TrueFlag
    summary: list[JobSummary]
    verification: Verification
    artifacts: list[ArtifactRow]
    session: SessionReceipt | None = None
    gui: GuiObservation | None = None
    summary_count: Count | None = None
    artifact_count: Count | None = None
    manifest_artifact_id: ArtifactId | None = None


class WorkflowSucceededJob(JobBase):
    state: Literal["succeeded"]
    terminal: TrueFlag
    summary: list[FitSummary | PlotSummary]
    verification: WorkflowVerification
    artifacts: list[ArtifactRow]
    summary_count: Count | None = None
    artifact_count: Count | None = None
    manifest_artifact_id: ArtifactId | None = None


type WorkflowJobOutput = PendingJob | UnsuccessfulJob | WorkflowSucceededJob


type JobOutput = PendingJob | UnsuccessfulJob | SucceededJob


class ArtifactPagination(OutputModel):
    offset: Count
    next_offset: Count | None
    total_chars: Count

    @model_validator(mode="after")
    def valid_page(self):
        if self.offset > self.total_chars:
            raise ValueError("Text offset exceeds artifact length")
        if self.next_offset is not None and not self.offset < self.next_offset < self.total_chars:
            raise ValueError("Next text offset must advance within the artifact")
        return self


class ArtifactOutput(OutputModel):
    artifact_id: ArtifactId
    local_path: str
    bytes: Count
    sha256: Sha256
    mime_type: str
    mode: Literal["info", "preview", "text", "download"]
    content_index: Literal[2] | None = None
    pagination: ArtifactPagination | None = None

    @model_validator(mode="after")
    def content_mode(self):
        if (self.mode != "info") != (self.content_index is not None):
            raise ValueError("Non-info artifact results identify their existing MCP content block")
        if (self.mode == "text") != (self.pagination is not None):
            raise ValueError("Only text results carry pagination metadata")
        return self


class ReadbackSpec(OutputModel):
    expression: str
    type: Literal["number", "string"]
    expected: float | str | None
    tolerance: float


class ProgramSpec(OutputModel):
    title: str
    language: Literal["python", "labtalk", "origin_c"]
    code: str
    entrypoint: str | None
    inputs: dict[str, str]
    project_path: str | None
    project_artifact: str | None
    readbacks: dict[str, ReadbackSpec]
    graph_formats: list[Literal["png", "pdf", "svg"]]
    output_files: list[str]
    timeout_seconds: int
    revision: str


class SessionSpec(OutputModel):
    action: Literal["open", "execute", "checkpoint", "restore", "close", "gui"]
    request_id: str
    session_id: str | None
    expected_revision: Count
    title: str
    visible: bool
    program_plan_id: str | None
    checkpoint_id: str | None
    # Non-GUI session manifests contain null here. GUI manifests have no workflow.
    gui: None


class InspectProjectOutput(OutputModel):
    engine: Engine
    workflow: WorkflowSpec | ProgramSpec | SessionSpec
    project_index: ProjectIndex
    verification: Verification


OPERATION_OUTPUT_TYPES = {
    "origin_capabilities": CapabilitySearchOutput | CapabilityDetailOutput | CoverageOutput,
    "origin_run_program": JobOutput,
    "origin_session": JobOutput | SessionInspectOutput,
    "origin_gui": JobOutput,
    "origin_status": StatusOutput,
    "origin_import_table": DatasetOutput,
    "origin_inspect_dataset": DatasetOutput,
    "origin_plan_workflow": PlanOutput,
    "origin_run_workflow": WorkflowJobOutput,
    "origin_get_job": JobOutput,
    "origin_cancel_job": JobOutput,
    "origin_get_artifact": ArtifactOutput,
    "origin_inspect_project": InspectProjectOutput,
    "origin_recipe": PlanOutput | WorkflowJobOutput,
}
