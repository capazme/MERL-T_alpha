from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    ValidationError,
    model_validator,
    create_model,
)
from typing import List, Optional, Dict, Any, Literal, Type
import datetime

from .models import TaskType, TaskStatus
from .config import task_settings

def build_pydantic_model_from_schema(name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Dynamically builds a Pydantic model from a JSON-like schema definition.
    """
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])
    
    fields = {}
    for field_name, field_props in properties.items():
        field_type: Any
        type_str = field_props.get("type")

        if type_str == "string":
            if "enum" in field_props:
                field_type = Literal[tuple(field_props["enum"])]
            else:
                field_type = str
        elif type_str == "number":
            field_type = float
        elif type_str == "integer":
            field_type = int
        elif type_str == "array":
            items = field_props.get("items", {})
            item_type_str = items.get("type", "string")
            if item_type_str == "string":
                field_type = List[str]
            else:
                field_type = List[Any]
        else:
            field_type = Any

        if field_name in required_fields:
            fields[field_name] = (field_type, ...)
        else:
            fields[field_name] = (Optional[field_type], None)
            
    return create_model(name, **fields)


class TaskCreateFromYaml(BaseModel):
    task_type: str
    input_data: Dict[str, Any]


class TaskListFromYaml(BaseModel):
    tasks: List[TaskCreateFromYaml]


class CredentialBase(BaseModel):
    type: str
    value: str
    weight: float

class CredentialCreate(CredentialBase):
    pass

class Credential(CredentialBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    authority_score: float
    track_record_score: float
    baseline_credential_score: float
    credentials: List[Credential] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class ResponseBase(BaseModel):
    output_data: Dict[str, Any]
    model_version: str

class ResponseCreate(ResponseBase):
    pass

class Response(ResponseBase):
    id: int
    task_id: int
    generated_at: datetime.datetime
    feedback: List["Feedback"] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class FeedbackBase(BaseModel):
    accuracy_score: float
    utility_score: float
    transparency_score: float
    feedback_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class FeedbackCreate(FeedbackBase):
    user_id: int

class Feedback(FeedbackBase):
    id: int
    user_id: int
    response_id: int
    is_blind_phase: bool
    community_helpfulness_rating: int
    consistency_score: Optional[float] = None
    submitted_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class LegalTaskBase(BaseModel):
    task_type: TaskType
    input_data: Dict[str, Any]

class LegalTaskCreate(LegalTaskBase):
    @model_validator(mode="before")
    @classmethod
    def validate_input_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            task_type_str = data.get("task_type")
            input_data = data.get("input_data")

            if task_type_str and input_data:
                task_config = task_settings.task_types.get(task_type_str)
                if task_config and task_config.input_data:
                    # Basic validation: check if all required keys from task_config.input_data are present
                    required_keys = set(task_config.input_data.keys())
                    provided_keys = set(input_data.keys())
                    missing_keys = required_keys - provided_keys
                    if missing_keys:
                        raise ValueError(f"Missing required input fields for task '{task_type_str}': {list(missing_keys)}")
                    
                    # Additional validation can be added here as needed
        return data

class LegalTask(LegalTaskBase):
    id: int
    created_at: datetime.datetime
    status: str
    responses: List[Response] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class TaskStatusUpdate(BaseModel):
    status: TaskStatus

class TaskAssignmentCreate(BaseModel):
    user_id: int
    is_devils_advocate: bool = False

class TaskAssignment(BaseModel):
    task_id: int
    user_id: int
    is_devils_advocate: bool
    assigned_at: datetime.datetime

class BulkUserCreate(BaseModel):
    users: List[UserCreate]

class FeedbackRatingCreate(BaseModel):
    user_id: int
    helpfulness_score: int = Field(..., ge=1, le=5)
    reasoning: Optional[str] = None

class FeedbackRating(BaseModel):
    id: int
    user_id: int
    feedback_id: int
    helpfulness_score: int
    reasoning: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class BiasReport(BaseModel):
    id: int
    task_id: int
    user_id: int
    bias_type: str
    bias_score: float
    analysis_details: Optional[Dict[str, Any]] = None
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class YamlContentRequest(BaseModel):
    yaml_content: str

class ExportRequest(BaseModel):
    task_type: TaskType
    export_format: Literal["sft", "preference"]

class SystemMetrics(BaseModel):
    totalTasks: int
    totalUsers: int
    totalFeedback: int
    averageConsensus: float
    activeEvaluations: int
    completionRate: float

class AuthorityCalculationResponse(BaseModel):
    user_id: int
    authority_score: float
    baseline_credentials: float
    track_record: float
    recent_performance: float
    updated_at: datetime.datetime

class AuthorityStatistics(BaseModel):
    total_users: int
    mean_authority: float
    median_authority: float
    std_authority: float
    min_authority: float
    max_authority: float
    distribution: Dict[str, int]  # Bins for histogram

class DisagreementAnalysis(BaseModel):
    task_id: int
    disagreement_level: float
    consensus_threshold: float
    is_high_disagreement: bool
    position_distribution: Dict[str, float]
    entropy: float
    num_evaluators: int

class ComprehensiveBiasReport(BaseModel):
    task_id: int
    total_bias_score: float
    bias_dimensions: Dict[str, float]
    bias_reports: List[BiasReport]
    threshold_exceeded: bool
    recommendations: List[str]