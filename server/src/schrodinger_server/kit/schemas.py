from pydantic import UUID4, BaseModel, ConfigDict, Field


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IDSchema(Schema):
    id: UUID4 = Field(..., description="The ID of the object.")

    model_config = ConfigDict(
        # IMPORTANT: this ensures FastAPI doesn't generate `-Input` for output schemas
        json_schema_mode_override="serialization",
    )
