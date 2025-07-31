from pydantic import BaseModel, Field
from typing import List, Optional, Generic, TypeVar # Import Generic and TypeVar
from datetime import date, datetime

# Define a TypeVar for generic types
T = TypeVar('T')

# --- Response Models ---

class TopProduct(BaseModel):
    product_keyword: str = Field(..., description="The detected product keyword.")
    mention_count: int = Field(..., description="The number of times the product keyword was mentioned.")

class ChannelActivity(BaseModel):
    message_date: date = Field(..., description="The date of the activity.")
    message_count: int = Field(..., description="The number of messages posted on that date.")

class MessageSearchResult(BaseModel):
    message_id: int = Field(..., description="Unique ID of the Telegram message.")
    message_text: Optional[str] = Field(None, description="The full text of the message.")
    message_date: date = Field(..., description="The date the message was posted.")
    channel_name: Optional[str] = Field(None, description="The name of the Telegram channel.")

# Make APIResponse a generic class
class APIResponse(BaseModel, Generic[T]): # Inherit from Generic[T]
    status: str = Field("success", description="Status of the API request.")
    message: Optional[str] = Field(None, description="A descriptive message for the response.")
    data: Optional[T] = Field(None, description="The main data payload of the response.") # Use T here

# --- Request Models (if any complex ones were needed, simple queries don't need them much) ---
# Example:
# class SearchQuery(BaseModel):
#     query: str = Field(..., min_length=1, max_length=100, description="Keyword to search for.")
#     limit: int = Field(10, gt=0, description="Maximum number of results to return.")