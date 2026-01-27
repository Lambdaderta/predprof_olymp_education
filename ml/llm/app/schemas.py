from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal
from datetime import datetime

# Chat completions
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(0.95, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    stop: Optional[Union[str, List[str]]] = None

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo

# Text completions
class CompletionRequest(BaseModel):
    model: str
    prompt: Union[str, List[str]]
    stream: bool = False
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(0.95, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(512, gt=0)
    stop: Optional[Union[str, List[str]]] = None

# Models list
class ModelData(BaseModel):
    id: str
    object: str = "model"
    created: int = 1677610602
    owned_by: str = "local"

class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelData]