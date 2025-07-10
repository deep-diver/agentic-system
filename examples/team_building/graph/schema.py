from pydantic import BaseModel, Field
from typing import Optional

class Role(BaseModel):
    role: str = Field(description="A role")
    description: str = Field(description="A description of the role")

class Roles(BaseModel):
    roles: list[Role] = Field(description="A list of roles")

class Participant(BaseModel):
    name: str = Field(description="The name of the participant")
    role: str = Field(description="The role of the participant")
    experience_years: int = Field(description="The experience years of the participant")
    skills: list[str] = Field(description="The skills of the participant")
    reason_to_join: str = Field(description="Why this participant is perfect for this project")

class Participants(BaseModel):
    participants: list[Participant] = Field(description="A list of participants")