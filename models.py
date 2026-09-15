from typing import Optional, List, Any
from pydantic import BaseModel, Field


class Patient(BaseModel):
    age: Optional[Any] = None
    gender: Optional[str] = None


class Diagnosis(BaseModel):
    condition: str
    icd10: Optional[str] = None


class Medication(BaseModel):
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    duration: Optional[str] = None


class LabResult(BaseModel):
    test: str
    value: str
    unit: Optional[str] = None


class ExtractedNote(BaseModel):
    patient: Patient = Field(default_factory=Patient)
    chief_complaint: Optional[str] = None
    diagnoses: List[Diagnosis] = Field(default_factory=list)
    medications: List[Medication] = Field(default_factory=list)
    symptoms: List[str] = Field(default_factory=list)
    lab_results: List[LabResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)