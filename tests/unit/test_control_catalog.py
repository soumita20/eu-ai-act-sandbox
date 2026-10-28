"""Tests for the versioned Phase 1 control inventory."""

import unittest

from eu_ai_act_sandbox.compliance import load_phase1_control_catalog


class ControlCatalogTests(unittest.TestCase):
    def test_catalog_is_versioned_unique_and_covers_selected_gdpr_controls(self) -> None:
        catalog = load_phase1_control_catalog()
        ids = [item.control_id for item in catalog.controls]
        self.assertEqual(catalog.catalog_version, "phase1-controls-1.1.0")
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(catalog.controls), 30)
        self.assertEqual(len(catalog.by_framework("GDPR")), 11)
        self.assertEqual(catalog.get("article_6_2_annex_iii").implementation_status, "IMPLEMENTED")

    def test_legal_applicability_dates_and_transition_are_catalog_data(self) -> None:
        from datetime import date

        catalog = load_phase1_control_catalog()
        self.assertEqual(catalog.get("eu_ai_act_article5_5_1_ba").effective_from, date(2026, 12, 2))
        self.assertEqual(catalog.get("article_6_2_annex_iii").effective_from, date(2027, 12, 2))
        annex_i = catalog.get("article_6_1_annex_i")
        self.assertEqual(annex_i.effective_from, date(2028, 8, 2))
        article_50_2 = catalog.get("article_50_2_provider_marking")
        self.assertEqual(article_50_2.effective_from, date(2026, 8, 2))
        self.assertEqual(article_50_2.transitional_steps_deadline, date(2026, 12, 2))
        self.assertIn("Article 111(4)", article_50_2.temporal_rule)


if __name__ == "__main__":
    unittest.main()
