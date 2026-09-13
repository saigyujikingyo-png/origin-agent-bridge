"""Small, closed workflow vocabulary. No caller-supplied code or LabTalk."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
Text = Annotated[str, Field(min_length=1, max_length=160)]


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ChartStyle(ClosedModel):
    preset: Literal["report", "presentation"] = "report"
    x_label: Text | None = None
    y_label: Text | None = None
    width: int = Field(default=1200, ge=600, le=2400)
    plot: Literal["scatter", "line", "line_symbol"] = "scatter"
    x_tick_format: Literal["auto", "decimal", "scientific"] = "auto"
    y_tick_format: Literal["auto", "decimal", "scientific"] = "auto"
    colors: list[Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]] = Field(
        default_factory=list, max_length=12
    )


class Analysis(ClosedModel):
    kind: Literal["linear_fit", "beer_lambert"]
    intercept: Literal["free", "zero"]
    weighting: Literal["none"]
    unknown_absorbance: float | None = None
    path_length_cm: float | None = Field(default=None, gt=0)
    concentration_scale_molar: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def scientific_options(self):
        if self.kind != "beer_lambert" and any(
            x is not None
            for x in (self.unknown_absorbance, self.path_length_cm, self.concentration_scale_molar)
        ):
            raise ValueError("Beer-Lambert options require kind=beer_lambert")
        if (self.path_length_cm is None) != (self.concentration_scale_molar is None):
            raise ValueError("Molar absorptivity requires both path_length_cm and concentration_scale_molar")
        return self


class Panel(ClosedModel):
    dataset_id: Identifier
    x: Text
    y: list[Text] = Field(min_length=1, max_length=12)
    y_errors: dict[str, Text] = Field(default_factory=dict)
    title: Text = "Origin analysis"
    analysis: Analysis | None = None
    style: ChartStyle = Field(default_factory=ChartStyle)

    @field_validator("y")
    @classmethod
    def unique_y(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Y columns must be distinct")
        return values

    @model_validator(mode="after")
    def related_columns(self):
        if self.x in self.y:
            raise ValueError("X and Y must be different columns")
        if set(self.y_errors) - set(self.y):
            raise ValueError("Every error-bar mapping key must be a selected Y column")
        if self.analysis and self.analysis.kind == "beer_lambert" and len(self.y) != 1:
            raise ValueError("Beer-Lambert requires one absorbance column per panel")
        return self


class Workflow(ClosedModel):
    revision: Text | None = None
    panels: list[Panel] = Field(min_length=1, max_length=12)
    formats: list[Literal["png", "pdf", "svg"]] = Field(default_factory=lambda: ["png"])
    timeout_seconds: int = Field(default=180, ge=30, le=1800)

    @field_validator("formats")
    @classmethod
    def formats_unique(cls, values):
        return list(dict.fromkeys(["png", *values]))
