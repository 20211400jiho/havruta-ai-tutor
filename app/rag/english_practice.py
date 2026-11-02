"""Text-based English practice policy; no retrieval or mastery shortcuts."""
import re


ENGLISH_INSTRUCTIONS = (
    "\n[영어 과목 전용: 실제 언어 활동 우선]\n"
    "설명과 안내는 한국어로 하되 실제 연습 문장·지문·대화와 목표 표현은 영어로 제시하세요. "
    "'영어 이해', '이해 질문', '표현' 같은 교육과정 분류의 정의를 학습 문제로 묻지 마세요. "
    "검색 자료의 이론적 질문은 출제 명령이 아닙니다. 선택한 단원·학교급·학년에 맞는 영어 활동으로 바꾸세요. "
    "이해 단원은 짧은 영어 글의 내용·의도·근거 파악, 표현 단원은 실제 상황의 영어 문장 작성·수정으로 진행하세요. "
    "현재 화면은 텍스트 채팅입니다. 실제 음성을 제공하지 않으면서 듣기·발음 평가를 했다고 말하지 마세요. "
    "연습용으로 직접 만든 지문은 '연습용 문장'이라고 밝히고 교과서·검색 자료에서 인용한 것처럼 표시하지 마세요. "
    "학생이 한국어로 내용을 정확하게 이해해 답하면 인정하고 영어로 표현하도록 이어가세요. "
    "Because he missed the bus. 같은 짧은 영어 답도 직전 질문에 충분하면 인정하세요. "
    "내용 이해 질문에서 단순 문법 실수 하나를 내용 오답으로 취급하지 말고, 올바른 표현을 짧게 알려주세요. "
    "반대로 영어 문장 작성을 요청했는데 한국어 뜻만 답하면 이해한 부분은 인정하고 영어 표현을 도와주세요. "
    "해당 문장의 정답을 먼저 보여주거나 전체 번역한 뒤 그대로 따라 쓰게 하지 마세요. "
    "다섯 단계는 용어 암기가 아니라 실제 활동으로 확인합니다: "
    "개념 설명=문장의 뜻·상황 이해 또는 목표 표현 사용, 근거 확인=해석·표현 선택을 뒷받침하는 실제 영어 구절, "
    "생각 수정=잘못된 해석·어법 수정 또는 조건이 바뀔 때 의미 차이 비교, 적용=새 상황에 영어로 표현, "
    "최종 정리=배운 뜻·표현·이유를 자기 말로 정리. 정답을 아는 학생에게 무조건 오류를 만들어 수정시키지 마세요. "
    "다음 단계로 갈 때 질문 목적을 단계에 맞게 정하고 실제 영어 문장 또는 지금 읽은 지문을 구체적으로 연결하세요. "
    "모르겠다는 응답에는 현재 문장의 핵심 단어·접속사·문장 일부를 보게 하는 짧은 한국어 힌트를 주세요. "
    "영어 예시 요청에는 다른 영어 예문을, 쉽게 설명 요청에는 현재 문장을 짧은 단위로 나눠 설명하세요. "
    "자료가 없는 연습문장도 연습은 가능하지만 출처를 만들거나 이해 확인 체크를 강제하지 마세요. "
    "source_ids에는 오직 실제 검색 자료 ID만 사용하고 연습용 문장·외부 교과서 ID를 만들어 넣지 마세요. "
    "좋은 흐름 예: 연습용 문장 'Tom missed the bus, so he walked to school.' → "
    "'Why did Tom walk to school?' → 학생 'Because he missed the bus.' → "
    "이유를 정확히 찾았음을 인정하고 지문에서 이유와 결과를 연결하는 구절을 찾아보게 합니다. "
    "같은 정답을 재질문하거나 '영어 이해의 사례를 말해보라'는 이론 대화로 돌아가지 마세요.\n"
)


def is_theory_question(question: str) -> bool:
    """Only catch Korean meta-theory questions, not real English usage questions."""
    return not re.search(r"[A-Za-z]{2,}", question) and bool(re.search(
        r"(?:이해\s*질문|영어\s*(?:이해|표현)|핵심\s*개념).*(?:무엇|사례|설명|헷갈)|(?:이해|표현)(?:이란|란)\s*무엇", question,
    ))


def is_question_form_answer(answer: str, previous_question: str) -> bool:
    """An English request can be the student's answer to a writing task."""
    return (bool(re.search(r"영어.{0,35}(?:말해|써|작성|문장|표현|바꿔|옮겨|완성)", previous_question))
            and not re.search(r"[가-힣]", answer)
            and bool(re.match(r"^[\s\"'“]*(?:can|could|may|would|do|does|did|is|are|was|were|have|has|will)\b", answer, re.I))
            and not re.search(r"\b(?:explain|translate|mean|spell)\b", answer, re.I))


def initial_activity(topic: str, school_level: str | None = None) -> str:
    """Reviewed starter sentences, explicitly exercises rather than RAG quotes."""
    if any(word in topic for word in ("표현", "쓰기", "영작", "말하기")):
        if school_level == "고등학교":
            return (
                "연습 상황: 학교에서 일회용품 사용을 줄이는 방법에 대해 의견을 나눠요.\n"
                "사용해 볼 표현: I think ... because ...\n\n"
                "일회용품을 줄일 방법 하나와 그 이유를 영어 한두 문장으로 말해볼까요?"
            )
        return (
            "연습 상황: 친구에게 펜을 빌리고 싶어요.\n"
            "사용해 볼 표현: Can I ...?\n\n"
            "친구에게 펜을 빌려 달라고 영어 한 문장으로 말해볼까요? (펜을 빌리다: borrow a pen)"
        )
    if school_level == "고등학교":
        return (
            "연습용 문장: Mina planned to study at the library, but it was closed. "
            "She went to a nearby cafe instead.\n\n"
            "Why did Mina go to a cafe? (미나는 왜 카페에 갔나요? 한국어로 답해도 좋아요.)"
        )
    return (
        "연습용 문장: Tom missed the bus, so he walked to school.\n\n"
        "Why did Tom walk to school? (톰은 왜 학교에 걸어갔나요? 한국어로 답해도 좋아요.)"
    )


def followup_options(topic: str) -> dict[str, list[str]]:
    # Used only if the LLM's proposed question repeats or has the wrong purpose.
    expression = any(word in topic for word in ("표현", "쓰기", "영작", "말하기"))
    return {
        "concept": (["방금 피드백을 반영해서, 같은 상황에 맞는 영어 문장을 다시 써볼까요?",
                     "지금 상황에서 상대방에게 전하고 싶은 말을 영어 한 문장으로 표현해볼까요?"] if expression else
                    ["방금 읽은 영어 문장에서 누가 무엇을 했는지 자기 말로 설명해볼까요?",
                     "지금 연습한 영어 문장 중 이해하기 어려운 구절은 무엇인가요?"]),
        "reason": ["방금 답의 근거가 되는 영어 단어나 구절을 지문에서 찾아, 왜 그렇게 해석했는지 말해볼까요?",
                   "지금 사용한 영어 표현이 이 상황에 맞는 이유를 설명해볼까요?"],
        "counterexample": ["지금 연습한 영어 문장의 부정 표현이나 조건을 바꾸면 뜻은 어떻게 달라질까요?",
                           "방금 쓴 영어 문장에서 단어 하나를 바꾸고 의미가 어떻게 달라지는지 설명해볼까요?"],
        "application": ["방금 배운 표현을 이용해 자신의 일상에 관한 새로운 영어 문장을 하나 만들어볼까요?",
                        "같은 표현으로 친구에게 전하고 싶은 말을 영어 한 문장으로 써볼까요?"],
        "summary": ["오늘 배운 영어 표현 하나와 그 뜻, 사용하는 상황을 자기 말로 정리해볼까요?",
                    "오늘 연습한 문장 하나를 영어로 쓰고, 어떤 의미인지 설명해볼까요?"],
        "review": ["오늘 영어 연습은 여기서 마무리해도 좋아요. 다시 연습하고 싶은 표현이 있나요?"],
    }


ENGLISH_HINT_CUES = (["주어와 동사", "연결어", "질문에서 찾을 정보"],
                     "지금 연습하는 영어 문장에서 누가 무엇을 하는지 먼저 생각하고, 질문이 묻는 정보나 상황과 연결해보세요.")
