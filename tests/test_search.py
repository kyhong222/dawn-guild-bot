"""검색 기능 테스트"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.utils.mapleland import MaplelandAPI


class TestMaplelandSearch:
    """메랜지지 검색 테스트"""

    def setup_method(self):
        self.api = MaplelandAPI()

    # === 토큰화 테스트 ===
    def test_tokenize_basic(self):
        """기본 토큰화"""
        assert self.api._tokenize_query("파엘") == ["파", "엘"]

    def test_tokenize_with_number(self):
        """숫자 포함 토큰화"""
        assert self.api._tokenize_query("신점10") == ["신", "점", "10"]

    def test_tokenize_with_percent(self):
        """숫자+% 토큰화"""
        assert self.api._tokenize_query("신점10%") == ["신", "점", "10%"]

    # === 줄임말 매칭 테스트 ===
    def test_abbreviation_basic(self):
        """기본 줄임말: 파엘 → 파워 엘릭서"""
        assert self.api._match_abbreviation("파엘", "파워 엘릭서") == True

    def test_abbreviation_with_number(self):
        """숫자 포함: 신점10 → 신발 점프력 주문서 10%"""
        assert self.api._match_abbreviation("신점10", "신발 점프력 주문서 10%") == True

    def test_abbreviation_with_percent(self):
        """% 포함: 신점10% → 신발 점프력 주문서 10%"""
        assert self.api._match_abbreviation("신점10%", "신발 점프력 주문서 10%") == True

    def test_abbreviation_middle_char(self):
        """중간 글자: 신프10 → 신발 점프력 주문서 10%"""
        assert self.api._match_abbreviation("신프10", "신발 점프력 주문서 10%") == True

    def test_abbreviation_same_word_multi_token(self):
        """같은 단어 내 다중 토큰: 드샤보 → 드래곤 샤인보우"""
        assert self.api._match_abbreviation("드샤보", "드래곤 샤인보우") == True

    def test_abbreviation_with_colon(self):
        """콜론 포함: 블와둥 → 히든스트리트:블루 와이번의 둥지"""
        assert self.api._match_abbreviation("블와둥", "히든스트리트:블루 와이번의 둥지") == True

    def test_abbreviation_no_match(self):
        """매칭 안됨"""
        assert self.api._match_abbreviation("가나다", "파워 엘릭서") == False

    def test_abbreviation_wrong_order(self):
        """순서 틀림"""
        assert self.api._match_abbreviation("엘파", "파워 엘릭서") == False


class TestPercentConversion:
    """퍼 → % 치환 테스트"""

    def test_convert_in_search(self):
        """신점10퍼 → 신점10%"""
        import re
        query = "신점10퍼"
        converted = re.sub(r'(\d+)퍼', r'\1%', query)
        assert converted == "신점10%"

    def test_convert_multiple(self):
        """여러 개 치환"""
        import re
        query = "10퍼 60퍼"
        converted = re.sub(r'(\d+)퍼', r'\1%', query)
        assert converted == "10% 60%"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
