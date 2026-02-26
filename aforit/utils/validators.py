"""Input validation utilities."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class Validator:
    """Chainable input validator."""

    def __init__(self, value: Any, field_name: str = "value"):
        self.value = value
        self.field = field_name
        self._errors: list[str] = []

    def required(self) -> Validator:
        """Value must not be None or empty."""
        if self.value is None or (isinstance(self.value, str) and not self.value.strip()):
            self._errors.append(f"{self.field} is required")
        return self

    def string(self) -> Validator:
        """Value must be a string."""
        if self.value is not None and not isinstance(self.value, str):
            self._errors.append(f"{self.field} must be a string")
        return self

    def integer(self) -> Validator:
        """Value must be an integer."""
        if self.value is not None and not isinstance(self.value, int):
            self._errors.append(f"{self.field} must be an integer")
        return self

    def min_length(self, length: int) -> Validator:
        """String must have minimum length."""
        if isinstance(self.value, str) and len(self.value) < length:
            self._errors.append(f"{self.field} must be at least {length} characters")
        return self

    def max_length(self, length: int) -> Validator:
        """String must not exceed maximum length."""
        if isinstance(self.value, str) and len(self.value) > length:
            self._errors.append(f"{self.field} must not exceed {length} characters")
        return self

    def matches(self, pattern: str) -> Validator:
        """String must match regex pattern."""
        if isinstance(self.value, str) and not re.match(pattern, self.value):
            self._errors.append(f"{self.field} format is invalid")
        return self

    def in_range(self, min_val: float, max_val: float) -> Validator:
        """Numeric value must be in range."""
        if isinstance(self.value, (int, float)):
            if self.value < min_val or self.value > max_val:
                self._errors.append(f"{self.field} must be between {min_val} and {max_val}")
        return self

    def one_of(self, options: list[Any]) -> Validator:
        """Value must be one of the given options."""
        if self.value not in options:
            self._errors.append(f"{self.field} must be one of: {', '.join(str(o) for o in options)}")
        return self

    def is_url(self) -> Validator:
        """Value must be a valid URL."""
        if isinstance(self.value, str):
            parsed = urlparse(self.value)
            if not parsed.scheme or not parsed.netloc:
                self._errors.append(f"{self.field} must be a valid URL")
        return self

    def is_path(self, must_exist: bool = False) -> Validator:
        """Value must be a valid file path."""
        if isinstance(self.value, str):
            try:
                p = Path(self.value)
                if must_exist and not p.exists():
                    self._errors.append(f"{self.field} path does not exist: {self.value}")
            except (ValueError, OSError):
                self._errors.append(f"{self.field} is not a valid path")
        return self

    def is_email(self) -> Validator:
        """Value must be a valid email address."""
        if isinstance(self.value, str):
            pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            if not re.match(pattern, self.value):
                self._errors.append(f"{self.field} must be a valid email address")
        return self

    def custom(self, check: Callable[[Any], bool], message: str) -> Validator:
        """Apply a custom validation function."""
        if not check(self.value):
            self._errors.append(f"{self.field}: {message}")
        return self

    def validate(self) -> list[str]:
        """Return all validation errors."""
        return self._errors

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self._errors) == 0

    def raise_if_invalid(self):
        """Raise ValidationError if validation failed."""
        if self._errors:
            raise ValidationError(self.field, "; ".join(self._errors))


def validate(value: Any, field_name: str = "value") -> Validator:
    """Create a new validator for a value."""
    return Validator(value, field_name)


def validate_dict(data: dict[str, Any], rules: dict[str, Callable]) -> list[str]:
    """Validate a dictionary against a set of rules.

    Usage:
        errors = validate_dict(data, {
            "name": lambda v: validate(v, "name").required().string().min_length(1),
            "age": lambda v: validate(v, "age").required().integer().in_range(0, 150),
        })
    """
    all_errors = []
    for field, rule_fn in rules.items():
        value = data.get(field)
        validator = rule_fn(value)
        all_errors.extend(validator.validate())
    return all_errors
