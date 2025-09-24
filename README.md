# Trecasa Dynamic Agreements

This repository contains a lightweight Python toolchain for composing dynamic client agreements for Trecasa projects. Agreements are described with YAML templates that use double-brace placeholders (for example `{{ client.name }}`) and simple filters to adapt content, allowing you to toggle sections, iterate over deliverables, and format numbers as currency.

## Features

- **Template driven** – Author agreements in YAML with reusable sections.
- **Conditional content** – Render sections only when their `when` expression evaluates to `True`.
- **Data driven** – Supply engagement details through structured YAML data files.
- **CLI workflow** – Use the `trecasa-agreement` command to preview or export agreements as Markdown.

## Getting started

1. Ensure Python 3.9+ is installed.
2. (Optional) Install the project in editable mode to make the `trecasa-agreement` command available:

   ```bash
   pip install -e .
   ```

3. Render the sample agreement:

   ```bash
   python -m trecasa_quotes.cli generate \
     --template templates/consulting_agreement.yaml \
     --data examples/sample_agreement_data.yaml \
     --preview
   ```

   To write the agreement to a file, pass `--output output/agreement.md`.

## Template structure

Agreement templates live in `templates/` as JSON-formatted YAML files and are composed of ordered `content` blocks:

```yaml
title: "{{ project_name }} Services Agreement"
organization: "Trecasa"
sections:
  - heading: "Deliverables"
    content:
      - type: numbered
        each: deliverables
        template: "{{ item.title }} – {{ item.description }}"
  - heading: "Financing Options"
    when: pricing.installments
    content:
      - type: bullets
        each: pricing.installments
        template: "{{ item.due }}: {{ item.amount | currency }}"
```

Supported block types are:

- `paragraph` – renders a block of text using placeholder substitution.
- `bullets` – iterates over a list and prints bullet items (`item` and `index` are available during rendering).
- `numbered` – iterates over a list and prints a numbered list.

The optional `when` field evaluates truthiness of a dotted path (e.g. `pricing.installments`).

## Tests

Run the automated tests with:

```bash
python -m unittest discover -s tests
```

The tests validate template parsing, conditional rendering, and the custom currency filter.
