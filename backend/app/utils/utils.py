import time
from calendar import monthrange
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import arrow
from fastapi.responses import JSONResponse
# import emails
# from emails.template import JinjaTemplate
from jose import jwt
from pydantic import BaseModel
from app.core.config import settings


class FilterDuration(str, Enum):
    one_month = "last_one_month"
    six_month = "last_six_months"
    one_year = "last_one_year"
    five_year = "last_five_years"
    advanced = "advanced"


class APIResponseModel(BaseModel):
    status: bool
    message: Optional[str]


def get_ok_response(message: str, status_code: int):
    response = APIResponseModel(status=True, message=message).dict()
    return JSONResponse(status_code=status_code, content=response)


def get_error_response(message: str, status_code: int):
    response = APIResponseModel(status=False, message=message).dict()
    return JSONResponse(status_code=status_code, content=response)


def sanitise_objectid(o):
    return None if o is None else str(o)


def get_timestamp():
    return time.time_ns() // 1_000_000


def round_value(value, limit=4):
    return round(value, limit)


def send_email(
    email_to: str,
    subject_template: str = "",
    html_template: str = "",
    environment: Dict[str, Any] = {},
) -> None:
    assert settings.EMAILS_ENABLED, "no provided configuration for email variables"
    # message = emails.Message(
    #     subject=JinjaTemplate(subject_template),
    #     html=JinjaTemplate(html_template),
    #     mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    # )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    # response = message.send(to=email_to, render=environment, smtp=smtp_options)
    # logging.info(f"send email result: {response}")


def send_test_email(email_to: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    with open(Path(settings.EMAIL_TEMPLATES_DIR) / "test_email.html") as f:
        template_str = f.read()
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        environment={
            "project_name": settings.PROJECT_NAME,
            "email": email_to
        },
    )


def send_reset_password_email(email_to: str, email: str, token: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    with open(Path(settings.EMAIL_TEMPLATES_DIR) / "reset_password.html") as f:
        template_str = f.read()
    server_host = settings.SERVER_HOST
    link = f"{server_host}/reset-password?token={token}"
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        environment={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )


def send_new_account_email(email_to: str, username: str,
                           password: str) -> None:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    with open(Path(settings.EMAIL_TEMPLATES_DIR) / "new_account.html") as f:
        template_str = f.read()
    link = settings.SERVER_HOST
    send_email(
        email_to=email_to,
        subject_template=subject,
        html_template=template_str,
        environment={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": link,
        },
    )


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {
            "exp": exp,
            "nbf": now,
            "sub": email
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        decoded_token = jwt.decode(token,
                                   settings.SECRET_KEY,
                                   algorithms=["HS256"])
        return decoded_token["email"]
    except jwt.JWTError:
        return None


def get_dashboard_filter_date_range(filter_duration: FilterDuration,
                                    start_year: int, start_month: int,
                                    end_year: int, end_month: int):
    if start_year is None:
        start_year = datetime.now().year
    if start_month is None:
        start_month = 1
    if end_year is None:
        end_year = start_year
    if end_month is None:
        end_month = start_month

    if filter_duration != FilterDuration.advanced:

        end_date = arrow.get(datetime.now())
        if filter_duration == FilterDuration.one_month:
            start_date = end_date.shift(months=-1)
        elif filter_duration == FilterDuration.six_month:
            start_date = end_date.shift(months=-6)
        elif filter_duration == FilterDuration.one_year:
            start_date = end_date.shift(years=-1)
        elif filter_duration == FilterDuration.five_year:
            start_date = end_date.shift(years=-5)
    else:
        end_day = monthrange(year=end_year, month=end_month)[1]
        start_date = arrow.get(datetime(start_year, start_month, 1))
        end_date = arrow.get(end_year, end_month, end_day)

    start_date = start_date.datetime
    start_date = datetime(start_date.year, start_date.month, start_date.day, 0,
                          0)
    end_date = end_date.datetime
    end_date = datetime(end_date.year, end_date.month, end_date.day, 0, 0)
    return start_date.timestamp(), end_date.timestamp()


def get_month_range(filter_duration: FilterDuration, start_date, end_date):
    if filter_duration is not None:
        start_month = datetime.fromtimestamp(start_date).strftime('%b %Y')
        end_month = datetime.fromtimestamp(end_date).strftime('%b %Y')
    else:
        start_month = f"Jan {start_date.strftime('%Y')}"
        end_month = end_date.strftime('%b %Y')
    return start_month, end_month


def get_number_days(current_date, due_date):
    number_of_days_remaining = due_date - current_date
    number_of_days_remaining = number_of_days_remaining.days
    return number_of_days_remaining


def is_float(num):
    try:
        float(num)
        return True
    except ValueError:
        return False


def index_exists(ls, i):
    return (0 <= i < len(ls)) or (-len(ls) <= i < 0)
