from typing import List, Optional, Dict, Any
import os
import re
from dotenv import load_dotenv
from openai import OpenAI

from app.services.rag_retriever import search


load_dotenv()

# OpenAI client will read OPENAI_API_KEY from environment (loaded by python-dotenv)
client = OpenAI()


def _build_context_text(contexts: List[str]) -> str:
    if not contexts:
        return ""
    parts = []
    for i, ctx in enumerate(contexts, start=1):
        parts.append(f"[자료 {i}]\n{ctx}")
    return "\n\n---\n\n".join(parts)


def generate_tutor_answer(
    question: str,
    school_level: Optional[str] = None,
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    top_k: int = 3,
) -> Dict[str, object]:
    """검색 기반 또는 일반 GPT 답변을 생성합니다.

    반환값 형식:
    {
      "answer": str,
      "mode": "rag" | "general_gpt",
      "contexts": [str,...]
    }
    """
    # 검색: search()는 hits(list) 형태로 id, document, metadata, distance, lexical_score 포함
    hits = search(question, top_k=top_k, school_level=school_level, grade=grade, subject=subject)
    retrieved_contexts: List[str] = [item.get("document", "") for item in hits] if hits else []

    def should_use_rag(question_text: str, hits_list: List[Dict[str, Any]]) -> bool:
        # 1) 빈 결과면 사용 안 함
        if not hits_list:
            return False
        first = hits_list[0]
        try:
            distance = float(first.get("distance", 1.0))
        except Exception:
            distance = 1.0
        lexical = int(first.get("lexical_score", 0)) if first.get("lexical_score") is not None else 0

        # 2) distance threshold
        if distance > 0.32:
            return False

        # 3) 핵심 키워드가 문서에 존재하는지 확인 (간단 토큰 매칭)
        tokens = re.findall(r"[\w가-힣]+", question_text)
        tokens = [t.lower() for t in tokens if len(t) >= 2]
        doc_text = str(first.get("document", "")).lower()
        if tokens:
            found = any(token in doc_text for token in tokens)
            if not found:
                return False

        # 4) lexical_score가 0이고 distance가 임계치보다 크면 사용 안 함
        if lexical == 0 and distance > 0.32:
            return False

        return True

    use_rag = should_use_rag(question, hits)
    mode = "rag" if use_rag else "general_gpt"
    used_contexts: List[str] = retrieved_contexts if use_rag else []

    # Prompt assembly
    system_instructions = (
        "당신은 중/고등학생을 위한 친절한 과학·수학 튜터입니다. 아래 지침을 반드시 따르세요.\n"
        "1) 문체: 친근하고 간결하게 시작하세요. 예: '좋아, 내가 알아본 바로는...', '좋아, 쉽게 말하면...' 중 하나로 시작하세요.\n"
        "2) 구조: 개념 설명 → 간단한 예시(가능하면 간단한 정수/소수) → 핵심 정리 순으로 답하세요.\n"
        "3) 계산 예시 규칙: 계산 예시를 제시할 때는 반드시 스스로 계산을 검산하고, 정확한 값만 사용하세요.\n"
        "   확실하지 않으면 복잡한 소수 대신 정수나 단순한 값으로 예시를 단순화하세요.\n"
        "   계산 과정을 보여주고, 최종값은 검산한 정확한 숫자만 기재하세요.\n"
        "4) 수식 표기: 절대 LaTeX 구문(예: \\frac, $...$, \(...\), \[...\])을 사용하지 마세요.\n"
        "   대신 읽기 쉬운 인라인 표기 사용: 예: f(x) = (x² - 1) / (x - 1) 또는 a = 3x + 2 처럼 표기하세요.\n"
        "5) 전류 설명 규칙: 중학생 대상 과학 설명에서는 숫자 단위 예시를 가능하면 피하세요.\n"
        "   - '2암페어' 같은 구체적 수치 예시는 꼭 필요하지 않으면 사용하지 마세요.\n"
        "   - 암페어(A)는 전류의 단위이며, 전류 자체가 전하의 양이라는 점을 강조하세요.\n"
        "   - 간단한 설명 예시 문장: '전류는 전자가 전선이나 회로를 통해 이동할 때 생기는 흐름이야.'\n"
        "   - 이어서: '전류가 클수록 같은 시간 동안 회로를 지나가는 전하의 양이 많다' 정도로 설명하세요.\n"
        "   - 쿨롱(C) 같은 단위는 중학생에게 억지로 자세히 설명하지 마세요.\n"
        "6) 수치 발명 금지: 문맥(context)에 없는 구체적 수치나 세부값을 임의로 만들어내지 마세요.\n"
        "   필요한 경우에는 '예시' 또는 '단순화한 값'임을 분명히 하되, 가능하면 계산 과정을 제시하세요.\n"
        "7) 극한 예시 지침: 극한 개념을 설명할 때는 대수적 정리(예: f(x) = (x²-1)/(x-1) = x+1 for x != 1)와 함께\n"
        "   간단한 수치 예시를 정확히 제시하세요. 예: x = 1.1 → f(x) = 2.1, x = 0.9 → f(x) = 1.9.\n"
        "   극한 관련 마무리 질문은 앞에서 설명한 예시와 자연스럽게 이어지게 만드세요.\n"
        "   예: '여기서 한번 생각해보자. x = 1에서는 직접 계산할 수 없는데도, 왜 우리는 x가 1에 가까워질 때의 값을 따로 살펴볼까?'\n"
        "8) 마무리 질문: 계산형 질문보다 개념형 질문으로 만들어, 학생이 바로 답할 수 있는 구체적 질문으로 마무리하세요.\n"
        "   예: '여기서 한번 생각해보자. 전류가 더 세지면 전구의 밝기나 회로의 작동에는 어떤 변화가 생길까?'\n"
        "9) 제목 금지: '하브루타 질문:', '꼬리 질문:' 같은 딱딱한 제목을 사용하지 마세요.\n"
        "10) 금지 표현: 사용자에게 '데이터셋', 'RAG', '데이터셋 기반', '일반 지식 기반' 같은 단어를 노출하지 마세요.\n"
        "11) 난이도: 중학생/고등학생이 이해할 수 있게 쉬운 말로 설명하세요."
    )

    context_text = _build_context_text(used_contexts)

    # User message includes question and contexts when available
    if mode == "rag" and context_text:
        user_prompt = (
            f"다음 자료를 참고해서 학생 수준(중/고등학생)에게 알기 쉽게 답해줘.\n\n{context_text}\n\n"
            f"질문: {question}\n\n"
            "간결하고 친근하게 설명해줘."
        )
    else:
        user_prompt = (
            f"질문: {question}\n\n"
            "학생이 이해하기 쉬운 말로 개념 설명, 간단한 예시, 핵심 정리, 마지막에 질문 1개로 마무리해줘."
        )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        # New OpenAI SDK returns choices with message content
        answer_text = ""
        if response and getattr(response, "choices", None):
            first = response.choices[0]
            msg = getattr(first, "message", None)
            if isinstance(msg, dict):
                answer_text = msg.get("content", "")
            else:
                # sometimes message is an object with .content
                answer_text = getattr(msg, "content", "")
        elif isinstance(response, dict):
            # fallback for dict-shaped response
            choices = response.get("choices", [])
            if choices:
                answer_text = choices[0].get("message", {}).get("content", "")

    except Exception as exc:
        answer_text = f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {exc}"

    # Ensure answer starts friendly if model omitted
    if not answer_text.strip().startswith("좋아"):
        answer_text = "좋아, 쉽게 말하면...\n\n" + answer_text

    # 반환: contexts는 검색된 원본(디버깅용), used_contexts는 실제 사용된 컨텍스트
    return {
        "answer": answer_text,
        "mode": mode,
        "contexts": retrieved_contexts,
        "used_contexts": used_contexts,
    }
