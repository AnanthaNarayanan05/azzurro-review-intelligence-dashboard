from pydantic import BaseModel, ConfigDict, Field, field_validator


class AliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alias_normalised: str


class PropertyRead(BaseModel):
    id: int
    code: str
    name: str
    location: str | None
    is_active: bool
    review_count: int  # genuine imported reviews only
    synthetic_review_count: int  # clearly-labelled demo reviews, kept separate
    aliases: list[AliasRead]


def _strip(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class PropertyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str | None = Field(default=None, max_length=32, pattern=r"^[a-z0-9][a-z0-9-]*$")
    location: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank.")
        return value

    _location = field_validator("location")(_strip)


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank.")
        return value

    _location = field_validator("location")(_strip)


class AliasCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=200)
