"""Template engine for prompt construction and formatting."""

from __future__ import annotations

import re
from typing import Any

from jinja2 import Environment, BaseLoader, TemplateSyntaxError


class PromptTemplate:
    """Template for constructing LLM prompts with variable substitution.

    Supports both simple {variable} syntax and Jinja2 templates.
    """

    def __init__(self, template: str, use_jinja: bool = False):
        self.raw_template = template
        self.use_jinja = use_jinja

        if use_jinja:
            env = Environment(loader=BaseLoader(), autoescape=False)
            self._jinja_template = env.from_string(template)
        else:
            self._jinja_template = None

    def render(self, **kwargs: Any) -> str:
        """Render the template with provided variables."""
        if self.use_jinja and self._jinja_template:
            return self._jinja_template.render(**kwargs)
        return self._simple_render(kwargs)

    def _simple_render(self, variables: dict[str, Any]) -> str:
        """Simple {variable} substitution."""
        result = self.raw_template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    def get_variables(self) -> list[str]:
        """Extract variable names from the template."""
        if self.use_jinja:
            # Extract Jinja2 variables
            pattern = r"\{\{[\s]*(\w+)[\s]*\}\}"
            return list(set(re.findall(pattern, self.raw_template)))
        else:
            pattern = r"\{(\w+)\}"
            return list(set(re.findall(pattern, self.raw_template)))

    def validate(self, variables: dict[str, Any]) -> list[str]:
        """Check if all required variables are provided."""
        required = set(self.get_variables())
        provided = set(variables.keys())
        missing = required - provided
        return [f"Missing variable: {v}" for v in missing]


# Common prompt templates
TEMPLATES = {
    "summarize": PromptTemplate(
        "Summarize the following text concisely:\n\n{text}\n\nSummary:"
    ),
    "explain": PromptTemplate(
        "Explain the following in simple terms:\n\n{topic}\n\nExplanation:"
    ),
    "code_review": PromptTemplate(
        "Review the following {language} code for bugs, performance issues, "
        "and best practices:\n\n```{language}\n{code}\n```\n\nReview:"
    ),
    "refactor": PromptTemplate(
        "Refactor the following {language} code to improve readability "
        "and maintainability:\n\n```{language}\n{code}\n```\n\nRefactored code:"
    ),
    "test_gen": PromptTemplate(
        "Generate comprehensive unit tests for the following {language} code:\n\n"
        "```{language}\n{code}\n```\n\nTests:"
    ),
    "debug": PromptTemplate(
        "Debug the following {language} code. The error is: {error}\n\n"
        "```{language}\n{code}\n```\n\nAnalysis and fix:"
    ),
    "translate": PromptTemplate(
        "Translate the following code from {source_lang} to {target_lang}:\n\n"
        "```{source_lang}\n{code}\n```\n\nTranslated code:"
    ),
    "document": PromptTemplate(
        "Generate documentation for the following {language} code:\n\n"
        "```{language}\n{code}\n```\n\nDocumentation:"
    ),
}


def get_template(name: str) -> PromptTemplate | None:
    """Get a named template."""
    return TEMPLATES.get(name)


def render_template(name: str, **kwargs: Any) -> str:
    """Render a named template with variables."""
    template = TEMPLATES.get(name)
    if not template:
        raise ValueError(f"Unknown template: {name}. Available: {list(TEMPLATES.keys())}")
    return template.render(**kwargs)
