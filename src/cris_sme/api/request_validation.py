"""Validate local API intent and identifiers before worker or cloud activity."""
import re
import unicodedata


class PublicRequestError(ValueError):
    """An explicitly safe, application-authored error for an API client."""

    status = 400


def require_authorization(request: dict) -> None:
    if request.get("authorization_confirmed") is not True:
        raise PublicRequestError("authorization_confirmed must be the JSON boolean true before an assessment can run.")


def boolean_option(request: dict, field: str) -> bool:
    value = request.get(field, False)
    if type(value) is not bool:
        raise PublicRequestError(f"{field} must be a JSON boolean.")
    return value


def optional_text(request: dict, field: str, maximum: int = 256) -> str:
    value = request.get(field, "")
    if not isinstance(value, str):
        raise PublicRequestError(f"{field} must be a string.")
    if len(value) > maximum or any(unicodedata.category(char).startswith("C") for char in value):
        raise PublicRequestError(f"{field} is too long or contains unsupported control characters.")
    return value.strip()


def azure_inputs(request: dict) -> dict[str, str]:
    values = {key: optional_text(request, key, 36) for key in ("subscription_id", "tenant_id")}
    for key, value in values.items():
        if value and not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value):
            raise PublicRequestError(f"{key} must be a hyphenated UUID or blank.")
    values["organization_name"] = optional_text(request, "organization_name")
    return values


def aws_inputs(request: dict, *, require_role: bool = False) -> dict[str, str]:
    values = {
        "account_id": optional_text(request, "account_id", 12),
        "role_arn": optional_text(request, "role_arn", 2048),
        "external_id": optional_text(request, "external_id", 1224),
        "organization_name": optional_text(request, "organization_name"),
    }
    account, role, external = (values[key] for key in ("account_id", "role_arn", "external_id"))
    if account and not re.fullmatch(r"[0-9]{12}", account):
        raise PublicRequestError("account_id must contain exactly 12 ASCII digits or be blank.")
    if require_role and not role:
        raise PublicRequestError("role_arn is required.")
    if role:
        match = re.fullmatch(r"arn:(aws(?:-[a-z0-9]+)*):iam::([0-9]{12}):role/(.+)", role)
        if not match:
            raise PublicRequestError("role_arn must identify an IAM role with a 12-digit account ID.")
        resource = match[3]
        prefix, _, name = resource.rpartition("/")
        name = name if "/" in resource else resource
        if (not re.fullmatch(r"[A-Za-z0-9_+=,.@-]{1,64}", name)
                or (prefix and (len(prefix) + 2 > 512 or any(not 33 <= ord(c) <= 126 for c in prefix)))):
            raise PublicRequestError("role_arn contains an invalid role path or name.")
        if account and account != match[2]:
            raise PublicRequestError("account_id must match the account in role_arn.")
    if external and (not role or not re.fullmatch(r"[A-Za-z0-9_+=,.@:/-]{2,1224}", external)):
        raise PublicRequestError("external_id requires a role_arn and 2-1224 supported non-space characters.")
    return values


def public_targets(request: dict) -> list[str]:
    value = request.get("targets", [])
    if isinstance(value, str):
        value = value.splitlines()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise PublicRequestError("targets must be a list of strings or newline-separated string.")
    targets = [optional_text({"target": item}, "target", 2048) for item in value]
    targets = [item for item in targets if item]
    if not 1 <= len(targets) <= 10:
        raise PublicRequestError("Supply between 1 and 10 public-exposure targets.")
    return targets
