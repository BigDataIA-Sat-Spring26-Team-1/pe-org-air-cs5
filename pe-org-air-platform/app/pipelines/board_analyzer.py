import re
import httpx
import datetime
from decimal import Decimal
from typing import List, Tuple
from app.models.board import BoardMember, GovernanceSignal
from bs4 import BeautifulSoup
from app.config import settings


class BoardCompositionAnalyzer:
    """
    Analyze board composition for AI governance indicators.
    
    Scoring:
    - Tech committee exists: +15 points
    - AI expertise on board: +20 points
    - Data officer role: +15 points
    - Independent ratio > 0.5: +10 points
    - Risk committee tech oversight: +10 points
    - AI in strategic priorities: +10 points
    - Base: 20 points
    - Max: 100 points
    """

    BASE_SCORE = Decimal("20")
    MAX_SCORE = Decimal("100")

    # Scoring Weights
    SCORE_TECH_COMMITTEE = Decimal("15")
    SCORE_AI_EXPERTISE = Decimal("20")
    SCORE_DATA_OFFICER = Decimal("15")
    SCORE_INDEPENDENT_RATIO = Decimal("10")
    SCORE_RISK_OVERSIGHT = Decimal("10")
    SCORE_STRATEGIC_PRIORITY = Decimal("10")

    # AI expertise patterns
    AI_EXPERTISE_PATTERNS = [
        r'\bartificial\s+intelligence\b',
        r'\bmachine\s+learning\b',
        r'\bchief\s+data\s+officer\b',
        r'\bCDO\b',
        r'\bCAIO\b',
        r'\bchief\s+ai\b',
        r'\bchief\s+information\b',
        r'\bCIO\b',
        r'\btechnology\s+and\s+data\b',
        r'\bdigital\s+transformation\b',
        r'\banalytics\b',
        r'\bdigital\s+transformation\b',
    ]

    # Tech committee patterns
    TECH_COMMITTEE_PATTERNS = [
        r'\btechnology\s+committee\b',
        r'\btechnology\s+and\s+\w+\s+committee\b',
        r'\bdigital\s+(strategy\s+)?committee\b',
        r'\binnovation\s+committee\b',
        r'\bIT\s+committee\b',
        r'\bpublic\s+responsibility\s+and\s+technology\b',
        r'\btechnology\s+and\s+cybersecurity\b',
        r'\binformation\s+technology\s+committee\b',
    ]

    # Data officer patterns
    DATA_OFFICER_PATTERNS = [
        r'\bchief\s+data\s+officer\b',
        r'\bCDO\b',
        r'\bchief\s+ai\s+officer\b',
        r'\bCAIO\b',
        r'\bchief\s+analytics\s+officer\b',
        r'\bCAO\b',
        r'\bchief\s+digital\s+officer\b',
    ]

    # AI strategy patterns
    AI_STRATEGY_PATTERNS = [
        r'\bartificial\s+intelligence\b',
        r'\bmachine\s+learning\b',
        r'\bai\s+strategy\b',
        r'\bai\s+initiative',
        r'\bai\s+transformation\b',
        r'\bgenerative\s+ai\b',
        r'\bai\s+model'
    ]

    # Risk+tech patterns
    RISK_TECH_PATTERNS = [
        r'\btechnology\b',
        r'\bcyber(security)?\b',
        r'\bdigital\b',
        r'\bIT\b',
        r'\binformation\s+technology\b',
    ]

    SEC_ENDPOINT = "https://api.sec-api.io/directors-and-board-members"

    def __init__(self):
        self.confidence = None

    def analyze_board(
        self,
        company_id: str,
        ticker: str,
        members: List[BoardMember],
        committees: List[str],
        strategy_text: str = "",
    ) -> GovernanceSignal:
        """
        Analyze board for AI governance strength.
        """
        score = self.BASE_SCORE

        # Check for tech committee
        relevant_committees = []
        has_tech = False
        for c in committees:
            for pattern in self.TECH_COMMITTEE_PATTERNS:
                if re.search(pattern, c, re.IGNORECASE):
                    has_tech = True
                    relevant_committees.append(c)
                    break

        if has_tech:
            score += self.SCORE_TECH_COMMITTEE

        # Check for AI expertise on board
        ai_experts = []
        for member in members:
            has_match = any(
                re.search(pattern, member.bio, re.IGNORECASE) or 
                re.search(pattern, member.title, re.IGNORECASE)
                for pattern in self.AI_EXPERTISE_PATTERNS
            )
            
            if has_match:
                ai_experts.append(member.name)

        has_ai_expertise = len(ai_experts) > 0
        if has_ai_expertise:
            score += self.SCORE_AI_EXPERTISE

        # Check for data officer role
        has_data_officer = False
        for member in members:
            has_match = any(
                re.search(pattern, member.title, re.IGNORECASE) or
                re.search(pattern, member.bio, re.IGNORECASE)
                for pattern in self.DATA_OFFICER_PATTERNS
            )
            if has_match:
                has_data_officer = True
                break

        if has_data_officer:
            score += self.SCORE_DATA_OFFICER

        # Check independent ratio
        independent_count = sum(1 for member in members if member.is_independent)
        total_directors = len(members)

        independent_ratio = Decimal("0")
        if total_directors > 0:
            independent_ratio = Decimal(independent_count) / Decimal(total_directors)
            if independent_ratio > Decimal("0.5"):
                score += self.SCORE_INDEPENDENT_RATIO

        # Check risk committee oversight
        has_risk_tech_oversight = False
        for c in committees:
            if "risk" in c.lower():
                for pattern in self.RISK_TECH_PATTERNS:
                    if re.search(pattern, c, re.IGNORECASE):
                        has_risk_tech_oversight = True
                        if c not in relevant_committees:
                            relevant_committees.append(c)
                        break

        if has_risk_tech_oversight:
            score += self.SCORE_RISK_OVERSIGHT

        # Check AI in strategy
        has_ai_in_strategy = False
        if strategy_text:
            has_ai_in_strategy = any(
                re.search(pattern, strategy_text, re.IGNORECASE)
                for pattern in self.AI_STRATEGY_PATTERNS
            )

            if has_ai_in_strategy:
                score += self.SCORE_STRATEGIC_PRIORITY

        # Cap at 100
        score = min(score, self.MAX_SCORE)

        # Calculate confidence
        data_points = 0
        total_possible = 6

        if committees:
            data_points += 1
        if members:
            data_points += 1
        if any(member.bio for member in members):
            data_points += 1
        if strategy_text:
            data_points += 1
        if total_directors > 0:
            data_points += 1
        if any(member.committees for member in members):
            data_points += 1
        
        confidence = min(
            Decimal("0.5") + Decimal(data_points) / Decimal(total_possible * 2),
            Decimal("0.95")
        )
        
        self.confidence = confidence
        
        return GovernanceSignal(
            company_id=company_id,
            ticker=ticker,
            has_tech_committee=has_tech,
            has_ai_expertise=has_ai_expertise,
            has_data_officer=has_data_officer,
            has_risk_tech_oversight=has_risk_tech_oversight,
            has_ai_in_strategy=has_ai_in_strategy,
            tech_expertise_count=len(ai_experts),
            independent_ratio=independent_ratio,
            governance_score=score,
            confidence=confidence,
            ai_experts=ai_experts,
            relevant_committees=relevant_committees
        )

    def _calculate_tenure(self, date_str: str) -> int:
        """Calculate years of tenure from date string."""
        if not date_str:
            return 0

        match = re.search(r'\d{4}', str(date_str))
        if match:
            start_year = int(match.group())
            current_year = datetime.datetime.now().year
            return max(0, current_year - start_year)
        return 0

    def fetch_board_data(self, ticker: str) -> Tuple[List[BoardMember], List[str]]:
        """Fetches board data from sec-api.io with improved deduplication."""
        import structlog
        api_logger = structlog.get_logger()
        
        payload = {
            "query": f"ticker:{ticker}",
            "from": 0,
            "size": 1, 
            "sort": [{ "filedAt": { "order": "desc" } }]
        }

        headers = {
            "Authorization": settings.SEC_API_KEY.get_secret_value() if settings.SEC_API_KEY else "",
            "Content-Type": "application/json"
        }

        api_logger.debug("fetching_board_data", ticker=ticker)

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self.SEC_ENDPOINT, 
                    json=payload, 
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

            if not data.get('data') or len(data['data']) == 0:
                api_logger.warning("no_board_data_found", ticker=ticker)
                return [], []

            latest_filing = data['data'][0]
            api_directors = latest_filing.get('directors', [])
            
            # Sort by name length descending to ensure full names act as master records
            sorted_directors = sorted(api_directors, key=lambda x: len(x.get('name', '')), reverse=True)
            
            unique_members: Dict[str, BoardMember] = {}
            all_committees = set()

            for d in sorted_directors:
                name = d.get('name', 'Unknown').strip()
                if not name or name == 'Unknown':
                    continue
                    
                title = d.get('position', '') or ""
                tenure_years = self._calculate_tenure(d.get('dateFirstElected'))
                is_independent = bool(d.get('isIndependent'))

                qualifications = d.get('qualificationsAndExperience', [])
                bio_text = ", ".join(qualifications) if qualifications else ""
                
                committees_data = d.get('committeeMemberships', [])
                current_committees = []
                for c in committees_data:
                    c_name = c if isinstance(c, str) else c.get('name', '')
                    if c_name:
                        current_committees.append(c_name)
                        all_committees.add(c_name)

                # Normalize name for mapping
                clean_name = re.sub(r'^(Mr\.|Ms\.|Mrs\.|Dr\.|Messrs\.)\s+', '', name, flags=re.IGNORECASE)
                
                # Check for existing match using part-based subset analysis
                existing_key = None
                name_parts = set(clean_name.lower().replace('.', '').split())
                surname = clean_name.split()[-1].lower() if clean_name else ""
                
                for key in list(unique_members.keys()):
                    key_parts = set(key.lower().replace('.', '').split())
                    key_surname = key.split()[-1].lower() if key else ""
                    
                    if surname == key_surname:
                        # If surnames match, check if one set of name parts is a subset of the other
                        if name_parts.issubset(key_parts) or key_parts.issubset(name_parts):
                            existing_key = key
                            break
                
                current_member = BoardMember(
                    name=name,
                    title=title,
                    bio=bio_text,
                    is_independent=is_independent,
                    tenure_years=tenure_years,
                    committees=current_committees
                )

                if existing_key:
                    existing = unique_members[existing_key]
                    # Merge Logic: Keep richer information
                    # 1. Update master name if current one is longer
                    if len(name) > len(existing.name):
                        unique_members.pop(existing_key)
                        unique_members[clean_name] = current_member
                        target = current_member
                    else:
                        target = existing
                    
                    # 2. Combine and deduplicate committees
                    target.committees = list(set(target.committees + current_committees))
                    
                    # 3. Keep longer title and bio
                    if len(title) > len(target.title):
                        target.title = title
                    if len(bio_text) > len(target.bio):
                        target.bio = bio_text
                else:
                    unique_members[clean_name] = current_member

            final_members = list(unique_members.values())
            api_logger.info("board_members_resolved", ticker=ticker, original_count=len(api_directors), resolved_count=len(final_members))
            
            return final_members, list(all_committees)

        except Exception as e:
            api_logger.error("board_data_fetch_failed", error=str(e))
            return [], []