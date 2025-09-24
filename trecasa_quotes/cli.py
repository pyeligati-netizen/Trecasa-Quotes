"""Command line interface for Trecasa dynamic agreements."""
from __future__ import annotations

import argparse
from pathlib import Path

from .agreements import AgreementRenderer, AgreementTemplate, AgreementTemplateError, load_agreement_data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Trecasa agreements from YAML templates and data inputs.")
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser("generate", help="Render an agreement by combining a template and data file.")
    generate_parser.add_argument("--template", "-t", type=Path, required=True, help="Path to the YAML agreement template.")
    generate_parser.add_argument("--data", "-d", type=Path, required=True, help="Path to the YAML data file used to fill the agreement.")
    generate_parser.add_argument("--output", "-o", type=Path, help="Optional file to write the rendered agreement to.")
    generate_parser.add_argument("--preview", action="store_true", help="Print the rendered agreement to STDOUT.")

    explain_parser = subparsers.add_parser("explain", help="Show metadata about the template.")
    explain_parser.add_argument("template", type=Path, help="Template file to inspect.")

    return parser


def _cmd_generate(args: argparse.Namespace) -> int:
    try:
        template_model = AgreementTemplate.from_file(args.template)
        data_payload = load_agreement_data(args.data)
        renderer = AgreementRenderer()
        rendered = renderer.render(template_model, data_payload)
    except AgreementTemplateError as exc:
        print(f"Error: {exc}")
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Agreement written to {args.output}")

    if args.preview or not args.output:
        print(rendered)
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    try:
        template_model = AgreementTemplate.from_file(args.template)
    except AgreementTemplateError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Title: {template_model.title}")
    if template_model.metadata:
        print("Metadata:")
        for key, value in template_model.metadata.items():
            print(f"  {key}: {value}")
    print("Sections:")
    for index, section in enumerate(template_model.sections, start=1):
        print(f"  {index}. {section.heading}")
        if section.when:
            print(f"     when: {section.when}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "generate":
        return _cmd_generate(args)
    if args.command == "explain":
        return _cmd_explain(args)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
