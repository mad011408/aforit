"""Tests for validation utilities."""

import pytest

from aforit.utils.validators import Validator, validate, validate_dict, ValidationError


class TestValidator:
    def test_required_passes(self):
        v = validate("hello", "name").required()
        assert v.is_valid()

    def test_required_fails_none(self):
        v = validate(None, "name").required()
        assert not v.is_valid()

    def test_required_fails_empty(self):
        v = validate("", "name").required()
        assert not v.is_valid()

    def test_string(self):
        assert validate("hello", "x").string().is_valid()
        assert not validate(123, "x").string().is_valid()

    def test_min_length(self):
        assert validate("hello", "x").min_length(3).is_valid()
        assert not validate("hi", "x").min_length(3).is_valid()

    def test_max_length(self):
        assert validate("hi", "x").max_length(5).is_valid()
        assert not validate("hello world", "x").max_length(5).is_valid()

    def test_in_range(self):
        assert validate(5, "x").in_range(1, 10).is_valid()
        assert not validate(15, "x").in_range(1, 10).is_valid()

    def test_one_of(self):
        assert validate("a", "x").one_of(["a", "b", "c"]).is_valid()
        assert not validate("d", "x").one_of(["a", "b", "c"]).is_valid()

    def test_is_url(self):
        assert validate("https://example.com", "x").is_url().is_valid()
        assert not validate("not-a-url", "x").is_url().is_valid()

    def test_is_email(self):
        assert validate("user@example.com", "x").is_email().is_valid()
        assert not validate("not-email", "x").is_email().is_valid()

    def test_chaining(self):
        v = validate("hi", "name").required().string().min_length(5)
        assert not v.is_valid()
        errors = v.validate()
        assert len(errors) == 1

    def test_raise_if_invalid(self):
        with pytest.raises(ValidationError):
            validate(None, "name").required().raise_if_invalid()

    def test_custom(self):
        v = validate(7, "x").custom(lambda x: x % 2 == 0, "must be even")
        assert not v.is_valid()


class TestValidateDict:
    def test_validate_dict(self):
        data = {"name": "John", "age": 25}
        errors = validate_dict(data, {
            "name": lambda v: validate(v, "name").required().string(),
            "age": lambda v: validate(v, "age").required().integer().in_range(0, 150),
        })
        assert errors == []

    def test_validate_dict_errors(self):
        data = {"name": "", "age": -1}
        errors = validate_dict(data, {
            "name": lambda v: validate(v, "name").required(),
            "age": lambda v: validate(v, "age").in_range(0, 150),
        })
        assert len(errors) == 2
