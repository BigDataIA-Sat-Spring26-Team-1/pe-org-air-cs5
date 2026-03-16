# Prototyping/scoring_poc/test_board_analyzer.py

import unittest
from decimal import Decimal
from unittest.mock import patch, Mock, MagicMock
from board_analyzer import BoardCompositionAnalyzer, BoardMember, GovernanceSignal


class TestBoardCompositionAnalyzer(unittest.TestCase):
    """Comprehensive tests for BoardCompositionAnalyzer."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = BoardCompositionAnalyzer()

    def test_base_score_only(self):
        """Test that base score is 20 when no indicators are met."""
        signal = self.analyzer.analyze_board(
            company_id="test-123",
            ticker="TEST",
            members=[
                BoardMember(
                    name="John Doe",
                    title="Director",
                    bio="General business experience",
                    is_independent=False,
                    tenure_years=5,
                    committees=[]
                )
            ],
            committees=[],
            strategy_text=""
        )

        self.assertEqual(signal.governance_score, Decimal("20"))
        self.assertEqual(signal.company_id, "test-123")
        self.assertEqual(signal.ticker, "TEST")

    def test_tech_committee_scoring(self):
        """Test +15 points for technology committee."""
        test_cases = [
            ("Technology Committee", True),
            ("Digital Committee", True),
            ("Innovation Committee", True),
            ("IT Committee", True),
            ("Technology and Cybersecurity Committee", True),
            ("TECHNOLOGY COMMITTEE", True),
            ("Audit Committee", False),
            ("Compensation Committee", False),
        ]

        for committee_name, should_score in test_cases:
            with self.subTest(committee=committee_name):
                signal = self.analyzer.analyze_board(
                    company_id="test-123",
                    ticker="TEST",
                    members=[],
                    committees=[committee_name],
                    strategy_text=""
                )

                expected_score = Decimal("35") if should_score else Decimal("20")
                self.assertEqual(
                    signal.governance_score,
                    expected_score,
                    f"Committee '{committee_name}' should {'add' if should_score else 'not add'} points"
                )
                self.assertEqual(signal.has_tech_committee, should_score)

    def test_ai_expertise_in_bio_only(self):
        """Test +20 points for AI expertise in bio."""
        test_cases = [
            ("Director", "artificial intelligence expert", True, 50),
            ("Director", "machine learning background", True, 50),
            ("Director", "data science PhD", True, 50),
            ("Director", "digital transformation leader", True, 50),
            ("Director", "general business experience", True, 30),
            ("Director", "artificial intelligence expert", False, 40),
            ("Director", "general business experience", False, 20),
        ]

        for title, bio, is_independent, expected in test_cases:
            with self.subTest(bio=bio[:30], independent=is_independent):
                signal = self.analyzer.analyze_board(
                    company_id="test-123",
                    ticker="TEST",
                    members=[
                        BoardMember(
                            name="Jane Smith",
                            title=title,
                            bio=bio,
                            is_independent=is_independent,
                            tenure_years=3,
                            committees=[]
                        )
                    ],
                    committees=[],
                    strategy_text=""
                )

                self.assertEqual(signal.governance_score, Decimal(str(expected)))

    def test_ai_expertise_and_data_officer_overlap(self):
        """Test that CDO/CTO titles trigger BOTH AI expertise AND data officer."""
        signal = self.analyzer.analyze_board(
            company_id="test-123",
            ticker="TEST",
            members=[
                BoardMember(
                    name="Jane Smith",
                    title="Chief Data Officer",
                    bio="",
                    is_independent=False,
                    tenure_years=3,
                    committees=[]
                )
            ],
            committees=[],
            strategy_text=""
        )

        self.assertEqual(signal.governance_score, Decimal("55"))
        self.assertTrue(signal.has_ai_expertise)
        self.assertTrue(signal.has_data_officer)

    def test_cto_triggers_ai_only(self):
        """Test that CTO triggers AI expertise."""
        signal = self.analyzer.analyze_board(
            company_id="test-123",
            ticker="TEST",
            members=[
                BoardMember(
                    name="Bob Smith",
                    title="Chief Technology Officer",
                    bio="",
                    is_independent=False,
                    tenure_years=5,
                    committees=[]
                )
            ],
            committees=[],
            strategy_text=""
        )

        self.assertEqual(signal.governance_score, Decimal("40"))
        self.assertTrue(signal.has_ai_expertise)

    def test_multiple_ai_experts(self):
        """Test that multiple AI experts are tracked."""
        members = [
            BoardMember("Alice", "Director", "chief technology experience", True, 5, []),
            BoardMember("Bob", "Director", "machine learning expert", True, 3, []),
            BoardMember("Carol", "Director", "business experience", True, 7, []),
        ]

        signal = self.analyzer.analyze_board(
            company_id="test-123",
            ticker="TEST",
            members=members,
            committees=[],
            strategy_text=""
        )

        self.assertEqual(signal.tech_expertise_count, 2)
        self.assertIn("Alice", signal.ai_experts)
        self.assertIn("Bob", signal.ai_experts)
        self.assertNotIn("Carol", signal.ai_experts)
        self.assertEqual(signal.governance_score, Decimal("50"))

    def test_data_officer_in_bio(self):
        """Test data officer detection in bio text."""
        signal = self.analyzer.analyze_board(
            company_id="test-123",
            ticker="TEST",
            members=[
                BoardMember(
                    name="Jane Doe",
                    title="Board Member",
                    bio="Previously served as Chief Data Officer at TechCorp",
                    is_independent=True,
                    tenure_years=3,
                    committees=[]
                )
            ],
            committees=[],
            strategy_text=""
        )

        self.assertTrue(signal.has_data_officer)
        self.assertEqual(signal.governance_score, Decimal("65"))

    def test_independent_ratio_scoring(self):
        """Test +10 points for independent ratio > 0.5."""
        test_cases = [
            (3, 5, True, 30),
            (2, 3, True, 30),
            (1, 2, False, 20),
            (2, 5, False, 20),
            (0, 5, False, 20),
        ]

        for indep_count, total_count, should_score, expected_score in test_cases:
            with self.subTest(independent=indep_count, total=total_count):
                members = [
                    BoardMember(
                        name=f"Member {i}",
                        title="Director",
                        bio="",
                        is_independent=(i < indep_count),
                        tenure_years=5,
                        committees=[]
                    )
                    for i in range(total_count)
                ]

                signal = self.analyzer.analyze_board(
                    company_id="test-123",
                    ticker="TEST",
                    members=members,
                    committees=[],
                    strategy_text=""
                )

                self.assertEqual(signal.governance_score, Decimal(str(expected_score)))
                
                expected_ratio = Decimal(indep_count) / Decimal(total_count)
                self.assertEqual(signal.independent_ratio, expected_ratio)

    def test_risk_tech_oversight_scoring(self):
        """Test +10 points for risk committee with tech oversight."""
        test_cases = [
            ("Risk and Technology Committee", 45),
            ("Technology and Risk Committee", 45),
            ("Risk and Cybersecurity Committee", 30),
            ("Risk and Digital Committee", 45),
            ("Risk and IT Committee", 45),
            ("Risk Committee", 20),
            ("Technology Committee", 35),
            ("Audit Committee", 20),
        ]

        for committee_name, expected_score in test_cases:
            with self.subTest(committee=committee_name):
                signal = self.analyzer.analyze_board(
                    company_id="test-123",
                    ticker="TEST",
                    members=[],
                    committees=[committee_name],
                    strategy_text=""
                )
                    
                self.assertEqual(signal.governance_score, Decimal(str(expected_score)),
                    f"{committee_name} should score {expected_score}")

    def test_ai_strategy_scoring(self):
        """Test +10 points for AI in strategic priorities."""
        test_cases = [
            ("Our strategy focuses on artificial intelligence", True),
            ("We are investing in machine learning", True),
            ("Our AI strategy includes generative AI", True),
            ("AI transformation is a priority", True),
            ("Developing AI models for customers", True),
            ("Traditional business model", False),
            ("", False),
        ]

        for strategy_text, should_score in test_cases:
            with self.subTest(strategy=strategy_text[:50]):
                signal = self.analyzer.analyze_board(
                    company_id="test-123",
                    ticker="TEST",
                    members=[],
                    committees=[],
                    strategy_text=strategy_text
                )

                expected_score = Decimal("30") if should_score else Decimal("20")
                self.assertEqual(signal.governance_score, expected_score)
                self.assertEqual(signal.has_ai_in_strategy, should_score)

    def test_maximum_score(self):
        """Test that score caps at 100."""
        members = [
            BoardMember("Alice", "Chief AI Officer", "artificial intelligence expert", True, 5, []),
            BoardMember("Bob", "Director", "machine learning background", True, 3, []),
            BoardMember("Carol", "Director", "data science PhD", True, 7, []),
        ]

        committees = [
            "Technology Committee",
            "Risk and Cybersecurity Committee"
        ]

        signal = self.analyzer.analyze_board(
            company_id="test-123",
            ticker="TEST",
            members=members,
            committees=committees,
            strategy_text="Our AI strategy focuses on artificial intelligence and machine learning"
        )

        self.assertEqual(signal.governance_score, Decimal("100"))
        self.assertLessEqual(signal.governance_score, Decimal("100"))

    def test_comprehensive_scoring(self):
        """Test a realistic comprehensive scenario."""
        members = [
            BoardMember(
                name="Sarah Johnson",
                title="Executive",
                bio="expertise in machine learning and AI",
                is_independent=False,
                tenure_years=3,
                committees=["Technology Committee"]
            ),
            BoardMember(
                name="Michael Chen",
                title="Independent Director",
                bio="20 years in digital transformation",
                is_independent=True,
                tenure_years=5,
                committees=["Risk and Technology Committee"]
            ),
            BoardMember(
                name="Emily Davis",
                title="Independent Director",
                bio="Former CEO",
                is_independent=True,
                tenure_years=2,
                committees=["Audit Committee"]
            ),
            BoardMember(
                name="Robert Wilson",
                title="Chief Data Officer",
                bio="",
                is_independent=False,
                tenure_years=1,
                committees=[]
            ),
        ]

        committees = [
            "Technology Committee",
            "Risk and Technology Committee",
            "Audit Committee",
            "Compensation Committee"
        ]

        strategy_text = """
        Our strategic priorities include investing in artificial intelligence
        and machine learning capabilities to drive innovation and efficiency.
        """

        signal = self.analyzer.analyze_board(
            company_id="comp-456",
            ticker="TECH",
            members=members,
            committees=committees,
            strategy_text=strategy_text
        )

        self.assertEqual(signal.governance_score, Decimal("90"))
        self.assertTrue(signal.has_tech_committee)
        self.assertTrue(signal.has_ai_expertise)
        self.assertTrue(signal.has_data_officer)
        self.assertTrue(signal.has_risk_tech_oversight)
        self.assertTrue(signal.has_ai_in_strategy)

    def test_confidence_calculation(self):
        """Test confidence score based on data completeness."""
        signal_minimal = self.analyzer.analyze_board(
            company_id="test-123",
            ticker="TEST",
            members=[],
            committees=[],
            strategy_text=""
        )
        self.assertGreaterEqual(signal_minimal.confidence, Decimal("0.5"))
        self.assertLessEqual(signal_minimal.confidence, Decimal("0.95"))

        signal_complete = self.analyzer.analyze_board(
            company_id="test-123",
            ticker="TEST",
            members=[
                BoardMember("John", "Director", "tech expert", True, 5, ["Tech Committee"])
            ],
            committees=["Tech Committee"],
            strategy_text="AI strategy"
        )
        self.assertGreater(signal_complete.confidence, signal_minimal.confidence)
        self.assertLessEqual(signal_complete.confidence, Decimal("0.95"))

    def test_edge_case_empty_inputs(self):
        """Test handling of empty inputs."""
        signal = self.analyzer.analyze_board(
            company_id="",
            ticker="",
            members=[],
            committees=[],
            strategy_text=""
        )

        self.assertEqual(signal.governance_score, Decimal("20"))
        self.assertEqual(signal.independent_ratio, Decimal("0"))
        self.assertEqual(signal.tech_expertise_count, 0)


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestBoardCompositionAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    result = run_tests()

    print()
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")