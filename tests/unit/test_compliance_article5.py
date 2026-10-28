"""Import and exercise the bounded Article 5 compliance screen."""

from datetime import date
import unittest

from eu_ai_act_sandbox.compliance import (
    ARTICLE5_PROVISIONS,
    Article5Disposition,
    Article5Indicator,
    Article5IndicatorStatus,
    assess_article5_indicators,
)


class Article5ScreenTests(unittest.TestCase):
    def test_catalog_imports_and_complete_negative_screen_is_not_compliance_claim(self):
        indicators = tuple(
            Article5Indicator(
                provision=definition.provision,
                status=Article5IndicatorStatus.NOT_INDICATED,
                rationale="No indicator was reported in the reviewed profile.",
            )
            for definition in ARTICLE5_PROVISIONS
        )

        result = assess_article5_indicators(
            assessment_id="assessment-test",
            application_id="application-test",
            as_of_date=date(2026, 1, 1),
            legal_basis_version="eu-ai-act-2024-1689",
            indicators=indicators,
        )

        self.assertEqual(result.disposition, Article5Disposition.NO_INDICATOR_IDENTIFIED)
        self.assertEqual(len(result.indicators), len(ARTICLE5_PROVISIONS))
        self.assertIn("not legal advice", result.limitations[0])


if __name__ == "__main__":
    unittest.main()
