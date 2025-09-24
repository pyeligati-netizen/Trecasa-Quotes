import unittest
from pathlib import Path

from trecasa_quotes import AgreementRenderer, AgreementTemplate, AgreementTemplateError, load_agreement_data


def fixture_path(name: str) -> Path:
    return Path(__file__).parent.parent / name


class AgreementRenderingTest(unittest.TestCase):
    def test_rendering_includes_conditional_section(self) -> None:
        template = AgreementTemplate.from_file(fixture_path("templates/consulting_agreement.yaml"))
        data = load_agreement_data(fixture_path("examples/sample_agreement_data.yaml"))
        renderer = AgreementRenderer()

        output = renderer.render(template, data)

        self.assertIn("Financing Options", output)
        self.assertIn("$18,000.00", output)

        data_no_financing = dict(data)
        data_no_financing["pricing"] = {"total": 48000, "deposit": 12000}
        output_without_financing = renderer.render(template, data_no_financing)
        self.assertNotIn("Financing Options", output_without_financing)

    def test_invalid_template_raises_error(self) -> None:
        bad_template = fixture_path("tests") / "bad.yaml"
        bad_template.write_text("{}", encoding="utf-8")
        try:
            with self.assertRaises(AgreementTemplateError):
                AgreementTemplate.from_file(bad_template)
        finally:
            bad_template.unlink()

    def test_currency_filter_rejects_invalid_value(self) -> None:
        template = AgreementTemplate.from_dict(
            {
                "title": "Simple",
                "sections": [
                    {
                        "heading": "Pricing",
                        "content": [
                            {"type": "paragraph", "text": "{{ value | currency }}"},
                        ],
                    }
                ],
            }
        )
        renderer = AgreementRenderer()
        with self.assertRaises(AgreementTemplateError):
            renderer.render(template, {"value": "not-a-number"})


if __name__ == "__main__":
    unittest.main()
