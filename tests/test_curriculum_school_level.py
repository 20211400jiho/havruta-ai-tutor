from app.rag.curriculum import get_subject_catalog, is_valid_curriculum_selection, unit_matches_school_level


def test_catalog_hides_units_from_the_other_school_level():
    for subject in ("국어", "과학", "기술가정", "정보", "수학", "사회", "도덕"):
        catalog = get_subject_catalog(subject)
        for level in catalog["school_levels"]:
            for grade in level["grades"]:
                assert grade["units"]
                for unit in grade["units"]:
                    assert unit_matches_school_level(unit["code"], level["name"]), (subject, level["name"], unit["code"])


def test_middle_school_korean_no_longer_offers_high_school_unit():
    assert not is_valid_curriculum_selection("국어", "중학교", "1학년", "10공국1-01")
    assert is_valid_curriculum_selection("국어", "중학교", "1학년", "9국01")
    assert is_valid_curriculum_selection("국어", "고등학교", "1학년", "10공국1-01")
