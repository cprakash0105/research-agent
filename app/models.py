from pydantic import BaseModel, Field
from typing import TypedDict, Annotated, Any
from operator import add


class Source(BaseModel):
    title: str = ""
    url: str = ""
    content: str = ""
    query: str = ""


class AgentState(TypedDict):
    query: str
    sub_questions: list[str]
    sources: Annotated[list[Source], add]
    vector_store: Any  # FAISS index, not serializable
    analysis: str
    report: str
