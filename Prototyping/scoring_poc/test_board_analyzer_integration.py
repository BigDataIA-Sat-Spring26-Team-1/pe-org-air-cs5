import unittest
from board_analyzer import BoardCompositionAnalyzer, BoardMember
from decimal import Decimal


class TestAPIIntegration(unittest.TestCase):
    def setUp(self):
        self.analyzer = BoardCompositionAnalyzer()

    def test_fetch_apple_board_data(self):
        members, committees = self.analyzer.fetch_board_data("AAPL")

        self.assertGreater(len(members), 0, "Apple should have board members")

        if len(members) > 0:
            first_member = members[0]
            self.assertIsInstance(first_member, BoardMember)
            self.assertIsInstance(first_member.name, str)
            self.assertIsInstance(first_member.title, str)
            self.assertIsInstance(first_member.is_independent, bool)
            self.assertIsInstance(first_member.tenure_years, int)
            self.assertIsInstance(first_member.committees, list)

            print(f"\n[PASS] Found {len(members)} board members for AAPL")
            print(f"Example: {first_member.name} - {first_member.title}")

        self.assertGreater(len(committees), 0, "Apple should have committees")
        print(f"[PASS] Found {len(committees)} committees: {committees}")

    def test_fetch_microsoft_board_data(self):
        """Test fetching real board data for Microsoft (MSFT)."""
        members, committees = self.analyzer.fetch_board_data("MSFT")

        self.assertGreater(len(members), 0, "Microsoft should have board members")
        self.assertGreater(len(committees), 0, "Microsoft should have committees")

        print(f"\n[PASS] Found {len(members)} board members for MSFT")
        print(f"[PASS] Found {len(committees)} committees")


class TestAPIQuickCheck(unittest.TestCase):
    def test_api_connectivity(self):
        analyzer = BoardCompositionAnalyzer()

        print("\n" + "="*60)
        print("TESTING API CONNECTIVITY")
        print("="*60)

        members, committees = analyzer.fetch_board_data("AAPL")

        if len(members) > 0:
            print("[PASS] API connection successful!")
            print(f"[PASS] Retrieved {len(members)} board members")
            print(f"[PASS] Retrieved {len(committees)} committees")
            self.assertTrue(True)

        else:
            print("[FAIL] API call succeeded but returned no data")
            print("This could mean:")
            print("- Invalid API key")
            print("- Rate limit exceeded")
            print("- API endpoint changed")
            self.fail("API returned no data for AAPL")


class TestFullAnalysisPipeline(unittest.TestCase):
    def setUp(self):
        self.analyzer = BoardCompositionAnalyzer()

    def test_full_analysis_with_real_data(self):
        members, committees = self.analyzer.fetch_board_data("AAPL")
        
        self.assertGreater(len(members), 0, "Need board data for analysis")
        
        signal = self.analyzer.analyze_board(
            company_id="aapl-001",
            ticker="AAPL",
            members=members,
            committees=committees,
            strategy_text="Our focus on artificial intelligence and machine learning continues to drive innovation across our products."
        )

        self.assertEqual(signal.company_id, "aapl-001")
        self.assertEqual(signal.ticker, "AAPL")
        self.assertGreaterEqual(signal.governance_score, Decimal("20"))
        self.assertLessEqual(signal.governance_score, Decimal("100"))
        self.assertGreaterEqual(signal.confidence, Decimal("0.5"))
        self.assertLessEqual(signal.confidence, Decimal("0.95"))

        print(f"\n{'='*60}")
        print(f"APPLE GOVERNANCE ANALYSIS")
        print(f"{'='*60}")
        print(f"Governance Score: {signal.governance_score}")
        print(f"Confidence: {signal.confidence}")
        print(f"\nIndicators:")
        print(f"\tTech Committee: {signal.has_tech_committee}")
        print(f"\tAI Expertise: {signal.has_ai_expertise}")
        print(f"\tData Officer: {signal.has_data_officer}")
        print(f"\tRisk Tech Oversight: {signal.has_risk_tech_oversight}")
        print(f"\tAI in Strategy: {signal.has_ai_in_strategy}")
        print(f"\nMetrics:")
        print(f"\tTech Expertise Count: {signal.tech_expertise_count}")
        print(f"\tIndependent Ratio: {signal.independent_ratio}")
        if signal.ai_experts:
            print(f"\nAI Experts ({len(signal.ai_experts)}):")
            for expert in signal.ai_experts[:5]:
                print(f"\t- {expert}")
        if signal.relevant_committees:
            print(f"\nRelevant Committees:")
            for committee in signal.relevant_committees:
                print(f"  - {committee}")

    def test_invalid_ticker(self):
        members, committees = self.analyzer.fetch_board_data("INVALIDTICKER123")

        self.assertEqual(len(members), 0)
        self.assertEqual(len(committees), 0)
        print("\n[PASS] Invalid ticker correctly returns empty data")

    def test_api_error_handling(self):
        members, committees = self.analyzer.fetch_board_data("")

        self.assertEqual(len(members), 0)
        self.assertEqual(len(committees), 0)
        print("\n[PASS] Empty ticker handled gracefully")

    def test_tenure_calculation(self):
        test_cases = [
            ("July 2021", 2025, 4),
            ("2015", 2025, 10),
            ("January 2024", 2025, 1),
            ("December 2020", 2025, 5),
            ("2025", 2025, 0),
            ("", 2025, 0),
            (None, 2025, 0),
        ]

        for date_str, current_year, expected_tenure in test_cases:
            with self.subTest(date=date_str):
                from unittest.mock import patch
                with patch('board_analyzer.datetime') as mock_datetime:
                    mock_datetime.datetime.now.return_value.year = current_year
                    result = self.analyzer._calculate_tenure(date_str)
                    self.assertEqual(result, expected_tenure,
                        f"Date '{date_str}' in {current_year} should give {expected_tenure} years")


if __name__ == '__main__':
    unittest.main(verbosity=2)