"""Core agreement generation logic for Trecasa dynamic agreements."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence


class AgreementTemplateError(RuntimeError):
    """Raised when a template cannot be loaded or rendered."""


_PLACEHOLDER_PATTERN = re.compile(r"{{\s*([^{}|]+?)(?:\s*\|\s*([a-zA-Z_][a-zA-Z0-9_]*))?\s*}}")


def _format_currency(value: Any, currency_symbol: str = "$") -> str:
    """Render a numeric value as a currency string."""

    try:
        number = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive branch
        raise AgreementTemplateError(f"Cannot format {value!r} as currency: {exc}") from exc
    return f"{currency_symbol}{number:,.2f}"


_FILTERS = {
    "currency": _format_currency,
}


@dataclass
class ParagraphBlock:
    text: str


@dataclass
class BulletBlock:
    each: str
    template: str


@dataclass
class NumberedBlock:
    each: str
    template: str


SectionBlock = ParagraphBlock | BulletBlock | NumberedBlock


@dataclass
class AgreementSection:
    """Represents a section in the agreement."""

    heading: str
    blocks: List[SectionBlock] = field(default_factory=list)
    when: Optional[str] = None


class AgreementTemplate:
    """Loads and renders agreement templates written as JSON mappings."""

    def __init__(
        self,
        *,
        title: str,
        sections: Iterable[AgreementSection],
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.title = title
        self.sections = list(sections)
        self.metadata = dict(metadata or {})

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AgreementTemplate":
        if "title" not in data:
            raise AgreementTemplateError("Template must define a 'title'.")
        raw_sections = data.get("sections")
        if not isinstance(raw_sections, Sequence) or not raw_sections:
            raise AgreementTemplateError("Template must define at least one section in 'sections'.")
        sections: List[AgreementSection] = []
        for index, section_data in enumerate(raw_sections):
            if not isinstance(section_data, Mapping):
                raise AgreementTemplateError(f"Section {index} must be a mapping.")
            heading = section_data.get("heading")
            if heading is None:
                raise AgreementTemplateError(f"Section {index} is missing required 'heading'.")
            content = section_data.get("content")
            if not isinstance(content, Sequence) or not content:
                raise AgreementTemplateError(f"Section {index} must define a non-empty 'content' list.")
            blocks = _parse_blocks(content, section_label=f"section {index}")
            when = section_data.get("when")
            if when is not None and not isinstance(when, str):
                raise AgreementTemplateError(f"Section {index} condition must be a string if provided.")
            sections.append(
                AgreementSection(
                    heading=str(heading),
                    blocks=blocks,
                    when=str(when) if when is not None else None,
                )
            )
        metadata = {key: value for key, value in data.items() if key not in {"title", "sections"}}
        return cls(title=str(data["title"]), sections=sections, metadata=metadata)

    @classmethod
    def from_file(cls, path: Path | str) -> "AgreementTemplate":
        try:
            file_path = Path(path)
            loaded = json.loads(file_path.read_text(encoding="utf-8"))
        except OSError as exc:  # pragma: no cover - filesystem failure
            raise AgreementTemplateError(f"Unable to read template file: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise AgreementTemplateError(f"Unable to parse template file: {exc}") from exc
        if not isinstance(loaded, Mapping):
            raise AgreementTemplateError("Template file must contain a mapping at the top level.")
        return cls.from_dict(loaded)


def _parse_blocks(content: Sequence[Any], section_label: str) -> List[SectionBlock]:
    blocks: List[SectionBlock] = []
    for position, block in enumerate(content):
        if not isinstance(block, Mapping):
            raise AgreementTemplateError(f"{section_label} content entry {position} must be a mapping.")
        block_type = block.get("type")
        if block_type == "paragraph":
            text = block.get("text")
            if not isinstance(text, str):
                raise AgreementTemplateError(f"{section_label} paragraph block requires a string 'text'.")
            blocks.append(ParagraphBlock(text=text))
        elif block_type == "bullets":
            each = block.get("each")
            template = block.get("template")
            if not isinstance(each, str) or not isinstance(template, str):
                raise AgreementTemplateError(f"{section_label} bullets block requires 'each' and 'template' strings.")
            blocks.append(BulletBlock(each=each, template=template))
        elif block_type == "numbered":
            each = block.get("each")
            template = block.get("template")
            if not isinstance(each, str) or not isinstance(template, str):
                raise AgreementTemplateError(f"{section_label} numbered block requires 'each' and 'template' strings.")
            blocks.append(NumberedBlock(each=each, template=template))
        else:
            raise AgreementTemplateError(
                f"{section_label} content entry {position} has unsupported type '{block_type}'."
            )
    return blocks


def load_agreement_data(path: Path | str) -> Dict[str, Any]:
    """Load agreement input data from a JSON-formatted file."""

    file_path = Path(path)
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem failure
        raise AgreementTemplateError(f"Unable to read data file: {exc}") from exc
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise AgreementTemplateError(f"Unable to parse data file: {exc}") from exc
    if not isinstance(data, MutableMapping):
        raise AgreementTemplateError("Agreement data must be a mapping of keys to values.")
    return dict(data)


def _resolve_value(context: Mapping[str, Any], path: str, *, raise_if_missing: bool = True) -> Any:
    current: Any = context
    for segment in path.split("."):
        segment = segment.strip()
        if segment == "":
            raise AgreementTemplateError("Empty path segment in placeholder.")
        if isinstance(current, Mapping):
            if segment not in current:
                if raise_if_missing:
                    raise AgreementTemplateError(f"Key '{segment}' not found while resolving '{path}'.")
                return None
            current = current[segment]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
            try:
                index = int(segment)
            except ValueError as exc:
                raise AgreementTemplateError(f"Expected numeric index for list access in '{path}'.") from exc
            try:
                current = current[index]
            except IndexError as exc:
                raise AgreementTemplateError(f"Index {index} out of range while resolving '{path}'.") from exc
        else:
            if not hasattr(current, segment):
                if raise_if_missing:
                    raise AgreementTemplateError(f"Attribute '{segment}' not found while resolving '{path}'.")
                return None
            current = getattr(current, segment)
    return current


def _render_text(template_str: str, context: Mapping[str, Any]) -> str:
    def replacer(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        filter_name = match.group(2)
        value = _resolve_value(context, path)
        if filter_name:
            filter_func = _FILTERS.get(filter_name)
            if filter_func is None:
                raise AgreementTemplateError(f"Unknown filter '{filter_name}'.")
            value = filter_func(value)
        return str(value)

    return _PLACEHOLDER_PATTERN.sub(replacer, template_str)


def _evaluate_condition(condition: str, context: Mapping[str, Any]) -> bool:
    expr = condition.strip()
    negate = False
    if expr.startswith("not "):
        negate = True
        expr = expr[4:].strip()
    value = _resolve_value(context, expr, raise_if_missing=False)
    result = bool(value)
    return not result if negate else result


class AgreementRenderer:
    """Renders agreements using lightweight template substitution."""

    def render(self, template: AgreementTemplate, data: Mapping[str, Any]) -> str:
        context: Dict[str, Any] = {}
        context.update(template.metadata)
        context.update(data)

        title = _render_text(template.title, context)
        parts: List[str] = [f"# {title}", ""]

        for section in template.sections:
            if section.when and not _evaluate_condition(section.when, context):
                continue
            heading = _render_text(section.heading, context)
            parts.append(f"## {heading}")
            parts.append("")

            for block in section.blocks:
                if isinstance(block, ParagraphBlock):
                    parts.append(_render_text(block.text, context))
                    parts.append("")
                elif isinstance(block, BulletBlock):
                    items = _resolve_value(context, block.each, raise_if_missing=True)
                    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
                        raise AgreementTemplateError(
                            f"Expected iterable for bullet list at '{block.each}'."
                        )
                    for index, item in enumerate(items, start=1):
                        local_context = dict(context)
                        local_context.update({"item": item, "index": index})
                        parts.append(f"- {_render_text(block.template, local_context)}")
                    if items:
                        parts.append("")
                elif isinstance(block, NumberedBlock):
                    items = _resolve_value(context, block.each, raise_if_missing=True)
                    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
                        raise AgreementTemplateError(
                            f"Expected iterable for numbered list at '{block.each}'."
                        )
                    for index, item in enumerate(items, start=1):
                        local_context = dict(context)
                        local_context.update({"item": item, "index": index})
                        rendered_item = _render_text(block.template, local_context)
                        parts.append(f"{index}. {rendered_item}")
                    if items:
                        parts.append("")
                else:  # pragma: no cover - defensive
                    raise AgreementTemplateError("Unsupported block type encountered during rendering.")

        return "\n".join(parts).rstrip() + "\n"
