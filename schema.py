from pydantic import BaseModel, Field

class WhatsAppMessage(BaseModel):
    message_id: str
    # [Requirement] The JSON field is named "from", but that is a reserved keyword in Python.
    # We use Field(alias="from") to map JSON "from" -> Python "from_"
    from_: str = Field(alias="from")
    to: str
    ts: str
    text: str | None = None