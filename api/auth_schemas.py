from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from email_validator import EmailNotValidError, validate_email

DOMAIN = "university.edu.vn"


def university_email(value: str) -> str:
    try:
        address = validate_email(value.strip(), check_deliverability=False, allow_smtputf8=False)
    except EmailNotValidError as exc:
        raise ValueError("Email không hợp lệ") from exc
    if address.domain.lower() != DOMAIN:
        raise ValueError("Vui lòng sử dụng email trường có đuôi @university.edu.vn")
    # This application's identity policy treats mailbox names as case-insensitive.
    return address.normalized.lower()


class EmailBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def check_email(cls, value):
        return university_email(value)


class RegisterBody(EmailBody):
    name: str = Field(min_length=1, max_length=100)
    password: SecretStr = Field(min_length=15, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Vui lòng nhập họ tên")
        return value


class LoginBody(EmailBody):
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: SecretStr = Field(min_length=32, max_length=128)


class ResetBody(TokenBody):
    password: SecretStr = Field(min_length=15, max_length=128)


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str
    role: str


class AuthView(BaseModel):
    user: UserView
    csrfToken: str
    expiresAt: str


class MessageView(BaseModel):
    message: str
