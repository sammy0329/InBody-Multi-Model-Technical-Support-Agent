# 기술 스택 상세

> InBody Multi-Model Technical Support Agent 프로젝트에서 사용된 모든 기술의 선택 근거와 대안 비교를 정리한 문서이다.

---

## 1. 기술 스택 총괄

| 분류 | 기술 | 버전 | 대안 (고려했으나 선택하지 않은 것) | 선택 이유 |
|------|------|------|-----------------------------------|-----------|
| LLM 오케스트레이션 | LangGraph | >=0.2 | LangChain Agent, CrewAI, AutoGen | StateGraph 패턴으로 멀티 에이전트 워크플로우를 노드/엣지로 명시적 제어 가능 |
| LLM 모델 | OpenAI GPT-4o-mini | latest | GPT-4o, Claude, Gemini | 분류 태스크 충분 성능 + GPT-4o 대비 약 1/15 비용 |
| 임베딩 | OpenAI text-embedding-ada-002 | v2 | KoSBERT, multilingual-e5, BGE-M3 | LangChain 네이티브 통합 + 한영 혼용 매뉴얼 대응 다국어 지원 |
| 벡터 DB | ChromaDB | >=0.5 | FAISS, Weaviate, Pinecone | 개발환경 zero-config 임베디드 모드 + 컬렉션 단위 격리 |
| 구조화 DB | SQLite + aiosqlite | 3.x | PostgreSQL, MongoDB | 로컬 파일 기반 경량 DB + 비동기 지원, 프로덕션 전환 용이 |
| 백엔드 | FastAPI | >=0.115 | Flask, Django | async/await 네이티브 + SSE 스트리밍 + 자동 OpenAPI 문서 |
| 프론트엔드 | Streamlit | >=1.40 | React, Gradio | 채팅 UI 내장 컴포넌트로 빠른 프로토타이핑 |
| 컨테이너 | Docker Compose (로컬) / systemd (EC2) | v2 | Kubernetes | 로컬: Docker Compose, EC2: venv + systemd 직접 실행으로 메모리 절약 |
| 클라우드 | AWS EC2 (t3.micro, 프리 티어) | - | Lambda, ECS Fargate | 로컬 파일 DB 호환 + 프리 티어로 무료 운영 가능 |
| IaC | CloudFormation | - | Terraform, CDK | AWS 네이티브 + EventBridge/Lambda 스케줄링 통합 |
| 테스트 | pytest | >=8.0 | unittest | parametrize로 444개 케이스 효율 커버 + 플러그인 생태계 |
| 코드 품질 | Ruff | >=0.8 | Black + isort + flake8 | 단일 도구로 린팅 + 포매팅 통합 |
| 언어 | Python | 3.11+ | 3.12, 3.10 | 모던 타이핑 문법 + 라이브러리 호환성 균형 |
| 설정 관리 | pydantic-settings | v2 | python-dotenv 단독 | 타입 검증 + 환경변수 자동 바인딩 + 중첩 설정 지원 |

---

## 2. 카테고리별 상세 설명

### 2.1 AI/LLM Orchestration

#### LangGraph (>=0.2)

**What**: LangChain 팀이 개발한 그래프 기반 멀티 에이전트 오케스트레이션 프레임워크이다. `StateGraph`를 핵심 추상화로 사용하며, 노드(처리 단위)와 엣지(전이 조건)를 명시적으로 정의하여 에이전트 워크플로우를 구성한다.

**Why**: 본 프로젝트의 파이프라인은 "기종 식별 -> 의도 분류 -> 전문 에이전트 라우팅 -> 가드레일 검증"이라는 고정된 흐름을 따른다. LangChain Agent의 ReAct(Reasoning + Acting) 루프는 에이전트가 자율적으로 도구를 선택하고 반복하는 패턴인데, 이처럼 고정된 파이프라인에는 불필요한 반복과 예측 불가능한 분기가 발생한다. 비용 면에서도 ReAct 루프의 불필요한 LLM 호출이 누적되어 비효율적이다.

CrewAI와 AutoGen은 에이전트 간 "대화"를 통해 협업하는 패턴에 특화되어 있다. 그러나 본 프로젝트는 에이전트 간 협업이 아니라 라우터가 단일 전문 에이전트를 지명하여 위임하는 구조이다. 에이전트 간 대화는 불필요하며, 오히려 기종 간 정보 혼선의 위험을 높인다.

LangGraph는 조건부 엣지(`add_conditional_edges`)로 라우터 노드의 출력에 따라 4개 전문 에이전트 중 하나로 분기하는 로직을 코드 수준에서 명시적으로 제어할 수 있다. `MemorySaver` 체크포인터를 통해 멀티턴 대화의 상태를 자동으로 관리하며, `thread_id` 기반으로 대화 세션을 격리한다.

**How**: `StateGraph`에 노드 5개(기종 식별, 의도 분류, 전문 에이전트 x3~4, 가드레일)를 등록하고, 조건부 엣지 4개로 의도 분류 결과에 따른 분기를 제어한다. `MemorySaver` 체크포인터를 `compile()` 시 주입하여 멀티턴 대화를 지원한다. 각 노드는 `AgentState` TypedDict를 공유 상태로 사용한다.

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

graph = StateGraph(AgentState)
graph.add_node("identify_model", identify_model_node)
graph.add_node("classify_intent", classify_intent_node)
graph.add_node("route_agent", route_agent_node)
graph.add_node("guardrail", guardrail_node)

graph.add_conditional_edges(
    "classify_intent",
    route_by_intent,
    {
        "troubleshoot": "troubleshoot_agent",
        "install": "install_agent",
        "connect": "connect_agent",
        "clinical": "clinical_agent",
    }
)

app = graph.compile(checkpointer=MemorySaver())
```

**Trade-offs**: LangGraph는 LangChain 생태계에 강하게 결합되어 있어 LangChain 버전 업데이트에 영향을 받는다. 또한 ReAct 루프 대비 유연성이 떨어져, 워크플로우 변경 시 그래프 구조를 수정해야 한다. 디버깅 시 그래프 상태 추적이 직관적이지 않을 수 있다.

---

#### GPT-4o-mini

**What**: OpenAI의 경량 멀티모달 모델로, GPT-4o의 성능을 유지하면서 비용과 지연 시간을 대폭 낮춘 모델이다.

**Why**: 본 프로젝트의 LLM 호출은 크게 세 가지 유형으로 나뉜다. 첫째, 기종 식별(분류 태스크)은 사용자 입력에서 "InBody 770S", "InBody 970S" 등 기종명을 추출하는 것으로 GPT-4o-mini가 충분히 처리한다. 둘째, 의도 분류(분류 태스크)는 troubleshoot, install, connect, clinical 중 하나를 선택하는 것으로 역시 mini 수준으로 가능하다. 셋째, 에이전트 응답(생성 태스크)은 RAG로 검색된 매뉴얼 청크와 Tool Calling으로 조회한 구조화 데이터를 기반으로 답변을 정리하는 것인데, 정보가 이미 제공된 상태에서 정리하는 작업은 mini로 충분한 품질을 낸다.

GPT-4o 대비 약 1/15의 비용(입력 토큰 기준)이므로, 모든 노드에 GPT-4o-mini를 사용하면 월간 API 비용을 극적으로 절감할 수 있다. 라우터 노드는 `temperature=0`으로 결정론적 출력을, 에이전트 노드는 `temperature=0.3`으로 약간의 자연스러움을 부여한다.

Claude(Anthropic)와 Gemini(Google)도 고려했으나, LangChain/LangGraph 생태계와의 통합 성숙도, Tool Calling API의 안정성, 한국어 성능의 균형에서 OpenAI가 현 시점에서 가장 무난한 선택이었다. 프로젝트 설정(config)에 `gpt-4o`도 정의되어 있으나 실제 코드에서는 비용 최적화를 위해 사용하지 않는다.

**How**: 프로젝트 설정 파일에서 모델명을 중앙 관리하며, 노드별로 temperature를 차등 적용한다.

```python
# config.py
LLM_MODEL = "gpt-4o-mini"
ROUTER_TEMPERATURE = 0.0
AGENT_TEMPERATURE = 0.3

# 라우터 노드
router_llm = ChatOpenAI(model=LLM_MODEL, temperature=ROUTER_TEMPERATURE)

# 에이전트 노드
agent_llm = ChatOpenAI(model=LLM_MODEL, temperature=AGENT_TEMPERATURE)
```

**Trade-offs**: 복잡한 다단계 추론이 필요한 질문에서는 GPT-4o 대비 품질 저하가 발생할 수 있다. 특히 매뉴얼에 없는 정보를 추론해야 하는 엣지 케이스에서 한계가 드러난다. 이를 대비하여 config에 `gpt-4o` 설정을 유지하고, 환경변수 변경만으로 전환할 수 있도록 설계했다.

---

#### OpenAI text-embedding-ada-002

**What**: OpenAI의 텍스트 임베딩 모델로, 1536차원 벡터를 생성하며 다국어 텍스트를 지원한다.

**Why**: InBody 매뉴얼은 한국어와 영어가 혼용된 문서이다. 제품명(InBody 770S, InBody 970S), 에러코드(E001), 기술 용어(Bioelectrical Impedance Analysis)는 영문이고, 설명과 절차는 한국어로 작성되어 있다. 한국어 전용 임베딩(KoSBERT, KoSimCSE 등)은 한국어 단일 텍스트에서는 우수하지만, 한영 혼용 텍스트에서의 성능이 불안정하다. text-embedding-ada-002는 다국어 학습 데이터로 훈련되어 한영 혼용 문맥에서 안정적인 시멘틱 유사도를 제공한다.

또한 LangChain의 `OpenAIEmbeddings` 클래스와 네이티브 통합되어 별도의 모델 호스팅이나 추가 API 키 없이 동일한 OpenAI API 키로 사용할 수 있다. 이는 인프라 복잡도를 줄이고 관리 포인트를 최소화하는 데 기여한다.

**How**: LangChain의 `OpenAIEmbeddings`를 ChromaDB의 임베딩 함수로 주입한다.

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
vectorstore = Chroma(
    collection_name="inbody_770s",
    embedding_function=embeddings,
    persist_directory="./data/chroma"
)
```

**Trade-offs**: 한국어 전용 임베딩 대비 순수 한국어 텍스트에서의 시멘틱 정확도가 약간 떨어질 수 있다. 또한 OpenAI API에 대한 의존성이 높아져, API 장애 시 임베딩 생성과 검색이 모두 불가능해진다. 비용은 임베딩 호출당 미미하지만 대량 인제스트 시 누적될 수 있다.

---

### 2.2 Data Layer

#### ChromaDB (>=0.5)

**What**: Python 네이티브 오픈소스 벡터 데이터베이스로, 임베디드 모드(프로세스 내 실행)와 클라이언트-서버 모드를 모두 지원한다.

**Why**: 개발 환경에서 별도의 서버 프로세스나 Docker 컨테이너 없이 Python 프로세스 내에서 바로 실행되는 zero-config 특성이 가장 큰 선택 이유이다. FAISS는 메타데이터 필터링이 기본 지원되지 않아 기종별 격리에 추가 구현이 필요하다. Weaviate와 Pinecone은 별도 서버/클라우드 서비스가 필요하여 로컬 개발 환경의 복잡도를 높인다.

본 프로젝트는 기종별 4개 컬렉션(270S, 580, 770S, 970S)과 시멘틱 캐시 1개 컬렉션, 총 5개 컬렉션을 운영한다. ChromaDB의 컬렉션 단위 격리는 기종 간 정보 혼선을 물리적 수준에서 방지하는 1차 방어선 역할을 한다. cosine distance를 유사도 메트릭으로 사용하며, 메타데이터 필터링으로 2차 논리적 격리를 적용한다.

프로덕션 환경에서는 Pinecone으로 전환할 수 있도록 `pyproject.toml`의 `[prod]` 의존성 그룹에 Pinecone 클라이언트를 포함시켜 두었다.

**How**: 기종별 컬렉션을 생성하고, RAG 검색 시 해당 기종의 컬렉션에서만 검색한다.

```python
# 기종별 컬렉션 생성 (COLLECTION_NAMES = {model: f"inbody_{model.lower()}" for model in VALID_MODELS})
collections = {
    "270S": Chroma(collection_name="inbody_270s", ...),
    "580": Chroma(collection_name="inbody_580", ...),
    "770S": Chroma(collection_name="inbody_770s", ...),
    "970S": Chroma(collection_name="inbody_970s", ...),
}

# 시멘틱 캐시 컬렉션
semantic_cache = Chroma(collection_name="semantic_cache", ...)

# 검색 시 기종별 컬렉션 선택
def retrieve(model: str, query: str):
    vectorstore = collections[model]
    return vectorstore.similarity_search(query, k=5)
```

**Trade-offs**: 임베디드 모드는 단일 프로세스에서만 접근 가능하여 수평 확장이 불가능하다. 대용량 데이터(수백만 벡터)에서의 성능이 Pinecone이나 Weaviate 대비 떨어진다. 파일 시스템 기반 영속화(persistence)는 서버리스 환경에서 사용할 수 없다.

---

#### SQLite + aiosqlite

**What**: SQLite는 파일 기반 경량 관계형 데이터베이스이며, aiosqlite는 SQLite의 비동기 래퍼이다.

**Why**: 에러코드 테이블, 주변기기 호환성 테이블 같은 구조화 데이터는 벡터 검색이 아닌 정확한 키 기반 조회가 필요하다. "E001 에러가 뭐야?"라는 질문에 시멘틱 검색으로 유사한 문서를 찾는 것이 아니라, 에러코드 테이블에서 E001을 정확히 조회해야 한다. 이를 위해 관계형 DB가 필요하다.

PostgreSQL은 프로덕션에 적합하지만 로컬 개발 환경에서 별도 서버를 띄워야 하는 부담이 있다. MongoDB는 스키마리스 특성이 에러코드 같은 고정 스키마 데이터에 불필요한 유연성을 제공한다. SQLite는 파일 하나로 동작하여 ChromaDB와 마찬가지로 zero-config 개발이 가능하다.

FastAPI의 비동기 엔드포인트에서 SQLite를 동기적으로 호출하면 이벤트 루프가 블로킹된다. aiosqlite는 별도 스레드에서 SQLite를 실행하여 이 문제를 해결한다. SQLAlchemy의 asyncio 확장과 함께 사용하여 비동기 ORM을 구성한다.

프로덕션 전환 시 `STRUCTURED_DB_URL` 환경변수를 `sqlite+aiosqlite:///data/inbody.db`에서 `postgresql+asyncpg://...`로 변경하는 것만으로 PostgreSQL로 전환할 수 있다. SQLAlchemy ORM을 사용하므로 쿼리 코드 변경이 불필요하다.

**How**: SQLAlchemy asyncio를 통해 비동기 세션을 관리한다.

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(settings.STRUCTURED_DB_URL)

async def get_error_code(code: str, model_id: str) -> ErrorCode:
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(ErrorCode).where(
                ErrorCode.code == code,
                ErrorCode.model_id == model_id
            )
        )
        return result.scalar_one_or_none()
```

**Trade-offs**: SQLite는 동시 쓰기에 약하다(WAL 모드에서도 단일 writer). 프로덕션에서 다수 사용자가 동시에 접근하면 병목이 발생할 수 있다. 이는 PostgreSQL 전환으로 해결한다.

---

#### RAG Pipeline

**What**: PDF 매뉴얼을 청크로 분할하여 벡터 DB에 저장하고, 사용자 질문과 유사한 청크를 검색하여 LLM에 컨텍스트로 제공하는 파이프라인이다.

**Why**: `PyPDFLoader`로 PDF를 페이지 단위로 로드한 뒤, `RecursiveCharacterTextSplitter`로 1024자 청크, 200자 오버랩으로 분할한다. 1024자로 설정한 이유는 InBody 매뉴얼의 한 섹션(설치 단계 하나, 에러 해결 절차 하나)이 평균 800~1200자이기 때문이다. 이 크기로 분할하면 하나의 청크가 하나의 완결된 정보 단위를 포함할 확률이 높다.

200자 오버랩은 청크 경계에서 문맥이 끊기는 것을 방지한다. 예를 들어 "1단계: 전원을 끕니다"로 끝나는 청크와 "2단계: USB를 연결합니다"로 시작하는 청크 사이에 200자가 겹치면, 검색 시 어느 청크를 가져와도 앞뒤 문맥을 확인할 수 있다.

**How**: 인제스트 파이프라인에서 기종별로 분리하여 각 컬렉션에 저장한다.

```python
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

loader = PyPDFLoader("data/manuals/770S/InBody770S_manual.pdf")
documents = loader.load()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1024,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", " ", ""]
)
chunks = splitter.split_documents(documents)

# 기종별 컬렉션에 저장
vectorstore = collections["770S"]
vectorstore.add_documents(chunks)
```

**Trade-offs**: 고정 크기 분할은 표나 리스트 같은 구조화된 콘텐츠를 중간에서 자를 수 있다. 시멘틱 분할(semantic chunking)이 더 정교하지만 구현 복잡도와 비용이 높아 현 단계에서는 고정 크기를 선택했다.

---

### 2.3 Backend

#### FastAPI (>=0.115)

**What**: Python의 고성능 비동기 웹 프레임워크로, Starlette(ASGI)과 Pydantic(데이터 검증)을 기반으로 한다.

**Why**: 본 프로젝트의 백엔드는 세 가지 핵심 요구사항을 가진다. 첫째, LLM API 호출은 수 초가 걸리므로 비동기 처리가 필수이다. FastAPI는 `async/await`를 네이티브로 지원하여 LLM 호출 대기 중에도 다른 요청을 처리할 수 있다. Flask는 기본적으로 동기 기반이며, 비동기 지원(Flask + asyncio)은 추가 설정이 필요하고 생태계 지원이 제한적이다.

둘째, 에이전트 응답을 실시간으로 스트리밍해야 한다. FastAPI의 `StreamingResponse`와 SSE(Server-Sent Events)를 조합하면 LLM의 토큰 생성을 실시간으로 클라이언트에 전달할 수 있다. 셋째, API 문서 자동 생성이 필요하다. FastAPI는 Pydantic 모델에서 자동으로 OpenAPI(Swagger) 문서를 생성하여 프론트엔드 개발자나 테스터가 별도 문서 없이 API를 탐색할 수 있다.

Django는 ORM, Admin, 인증 등 풀스택 기능을 제공하지만, 본 프로젝트는 API 서버 역할만 하므로 불필요한 기능이 오버헤드가 된다. Django REST Framework를 추가하더라도 비동기 지원이 FastAPI 대비 미성숙하다.

**How**: 비동기 엔드포인트와 SSE 스트리밍을 구현한다.

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(title="InBody Tech Support API")

@app.post("/chat")
async def chat(request: ChatRequest):
    async def event_stream():
        async for chunk in agent.astream(request.message):
            yield f"data: {chunk.json()}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**Trade-offs**: FastAPI는 Django 대비 내장 기능이 적어 인증, 권한 관리 등을 직접 구현하거나 서드파티 라이브러리를 사용해야 한다. 또한 Starlette/Pydantic 버전 업데이트 시 하위 호환성이 깨질 수 있다(Pydantic V1 -> V2 마이그레이션이 대표적 사례).

---

### 2.4 Frontend

#### Streamlit (>=1.40)

**What**: Python으로 데이터 앱과 프로토타입을 빠르게 구축할 수 있는 프레임워크이다. `st.chat_message`와 `st.chat_input` 컴포넌트로 채팅 인터페이스를 기본 제공한다.

**Why**: 프론트엔드 개발에 투입할 수 있는 리소스가 제한적인 상황에서 Streamlit은 압도적인 구현 속도를 제공한다. React로 채팅 UI를 구현하려면 컴포넌트 설계, 상태 관리, API 연동, 스타일링 등에 수일이 소요되지만, Streamlit은 `st.chat_message`/`st.chat_input` 조합으로 수 시간 내에 완성도 있는 채팅 UI를 구현할 수 있다.

Gradio도 빠른 프로토타이핑을 지원하지만, Streamlit이 채팅 UI 전용 컴포넌트를 더 풍부하게 제공하며, 세션 상태 관리(`st.session_state`)가 멀티턴 대화 관리에 적합하다. 또한 Streamlit의 커뮤니티와 문서가 더 활발하다.

본 프로젝트의 프론트엔드 목적은 프로토타입 시연과 내부 데모이므로, 커스텀 디자인보다 기능 구현 속도가 우선이다.

**How**: 세션 상태로 대화 이력을 관리하고, SSE를 통해 스트리밍 응답을 표시한다.

```python
import streamlit as st

st.title("InBody 기술 지원 에이전트")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("질문을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("assistant"):
        response = call_api(prompt)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
```

**Trade-offs**: 커스텀 스타일링이 제한적이다. 기업 CI/BI에 맞는 정교한 디자인이 필요하면 React로 전환해야 한다. 또한 Streamlit의 실행 모델(전체 스크립트 재실행)이 복잡한 상태 관리에서 예측하기 어려운 동작을 유발할 수 있다. 동시 접속자 수 증가 시 서버 리소스 소모가 크다.

---

### 2.5 Infrastructure

#### Docker Compose (로컬 개발) / systemd (EC2 배포)

**What**: 로컬 개발 환경에서는 Docker Compose로 2개 서비스를 실행하고, EC2 배포 환경에서는 Python venv + systemd로 직접 실행한다.

**Why**: 본 프로젝트는 API 서버(FastAPI, 포트 8000)와 UI 서버(Streamlit, 포트 8501)의 2개 서비스로 구성된다. 로컬 개발에서 Docker Compose는 `docker compose up -d` 한 줄로 전체 스택을 기동할 수 있어 간결하다.

그러나 EC2 배포 환경(t3.micro, 메모리 1GB)에서는 Docker 데몬 자체의 메모리 오버헤드(~200MB)가 부담된다. venv + systemd 방식은 Docker 없이 Python 프로세스를 직접 실행하여 메모리를 절약한다. systemd는 `Restart=always` 설정으로 프로세스 크래시 시 자동 재시작, `Requires`/`After` 설정으로 서비스 간 의존성 관리, `journalctl`로 로그 조회 등 Docker Compose와 동등한 서비스 관리 기능을 제공한다.

**How**: EC2에서는 2개의 systemd unit 파일로 서비스를 관리한다.

```ini
# deploy/inbody-api.service
[Service]
ExecStart=/home/ubuntu/InBody-Multi-Model-Technical-Support-Agent/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always

# deploy/inbody-ui.service
[Service]
Requires=inbody-api.service
ExecStart=.venv/bin/streamlit run ui/app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
```

**Trade-offs**: systemd 방식은 Docker의 이미지 빌드/배포, 환경 격리 이점을 포기한다. 의존성 변경 시 EC2에서 직접 `pip install`을 실행해야 하며, 호스트 OS에 직접 의존한다. 서비스 규모가 커지면 Docker 또는 ECS로 전환이 필요하다.

---

#### AWS EC2 (t3.micro, 프리 티어)

**What**: AWS 프리 티어 대상 인스턴스로, 신규 계정 기준 월 750시간 무료 사용이 가능하다. vCPU 2개, 메모리 1GB를 제공한다.

**Why**: ChromaDB와 SQLite가 모두 로컬 파일 시스템 기반이므로 서버리스(AWS Lambda)는 사용할 수 없다. Lambda는 실행 시 임시 파일 시스템(/tmp)만 제공하며, 함수 종료 시 데이터가 사라진다. EFS를 마운트하는 방법이 있지만 벡터 DB의 랜덤 I/O 패턴에서 성능이 크게 떨어진다.

t3.micro(vCPU 2, 메모리 1GB)는 데모 환경(동시 사용자 5명 이하)에서 충분한 사양이다. Docker를 사용하지 않고 venv + systemd로 직접 실행하여 메모리 오버헤드를 최소화하고, uvicorn worker를 1개로 운영한다. EventBridge + Lambda로 평일 09-19시 KST에만 운영하여 월 ~220시간만 사용하므로 프리 티어 범위(750시간) 내에서 운영 가능하다.

Elastic IP를 연결하여 EC2 stop/start 시에도 고정 IP를 유지한다.

**How**: CloudFormation 템플릿에서 EventBridge + Lambda 스케줄러를 정의하고, EC2 인스턴스의 자동 start/stop을 관리한다. 인스턴스 시작 시 systemd에 등록된 서비스가 자동으로 기동된다.

**Trade-offs**: t3.micro의 1GB 메모리는 동시 요청이 많아지면 OOM 위험이 있다. uvicorn worker를 1개로 제한하여 메모리를 관리하되, 동시 처리 능력이 떨어진다. 사용량 증가 시 t3.small(2GB) 이상으로 업그레이드가 필요하다. 프리 티어 기간(12개월) 종료 후에는 온디맨드 요금이 발생하므로 Spot 인스턴스 전환을 고려할 수 있다.

---

#### CloudFormation

**What**: AWS의 네이티브 IaC(Infrastructure as Code) 서비스로, YAML/JSON 템플릿으로 AWS 리소스를 선언적으로 관리한다.

**Why**: Terraform은 멀티 클라우드 지원이 장점이지만, 본 프로젝트는 AWS 단일 클라우드를 사용하므로 이 장점이 불필요하다. AWS CDK(Cloud Development Kit)는 Python으로 인프라를 정의할 수 있어 매력적이지만, CDK의 추상화 레이어가 추가적인 학습 곡선을 요구한다. CloudFormation은 AWS 콘솔과 직접 통합되어 스택 상태를 시각적으로 확인할 수 있고, 드리프트 감지(drift detection)로 수동 변경을 추적할 수 있다.

특히 EventBridge 규칙과 Lambda 함수를 CloudFormation 내에서 정의하여 평일 09-19시 KST 자동 운영 스케줄을 인프라 코드에 포함시킬 수 있다. 이를 통해 월간 인프라 비용을 약 $5 수준으로 유지한다(EC2 Spot ~$1.3 + EBS ~$2.3 + EIP ~$1.5).

**How**: CloudFormation 템플릿에서 EC2, EventBridge, Lambda를 정의한다.

```yaml
# 스케줄링 예시 (EventBridge 규칙)
StartRule:
  Type: AWS::Events::Rule
  Properties:
    ScheduleExpression: "cron(0 0 ? * MON-FRI *)"  # KST 09:00
    Targets:
      - Arn: !GetAtt StartStopLambda.Arn
        Input: '{"action": "start"}'

StopRule:
  Type: AWS::Events::Rule
  Properties:
    ScheduleExpression: "cron(0 10 ? * MON-FRI *)"  # KST 19:00
    Targets:
      - Arn: !GetAtt StartStopLambda.Arn
        Input: '{"action": "stop"}'
```

**Trade-offs**: CloudFormation의 YAML 문법은 장황하고 조건부 로직이 불편하다. Terraform의 HCL이나 CDK의 Python이 더 표현력이 높다. 또한 CloudFormation은 AWS 전용이므로 멀티 클라우드 전환 시 재작성이 필요하다.

---

### 2.6 Testing

#### pytest (>=8.0)

**What**: Python의 표준 테스트 프레임워크로, 간결한 assert 문법과 풍부한 플러그인 생태계를 제공한다.

**Why**: `unittest`는 Python 표준 라이브러리에 포함되어 있지만, 클래스 기반 테스트 구조와 `self.assertEqual` 등의 장황한 assert 메서드가 테스트 코드의 가독성을 떨어뜨린다. pytest는 함수 기반 테스트와 단순 `assert` 문으로 동일한 검증을 더 간결하게 수행한다.

본 프로젝트의 핵심 테스트 전략은 `@pytest.mark.parametrize`를 활용한 파라미터화 테스트이다. 4개 기종 x 4개 의도 x 다수의 질문 변형으로 구성된 444개 테스트 케이스를 소수의 테스트 함수로 커버한다. `unittest`에서 이를 구현하려면 `subTest` 컨텍스트 매니저를 사용해야 하는데, parametrize 대비 리포팅과 필터링 기능이 떨어진다.

커스텀 `SCMetricsCollector` 플러그인을 작성하여 SC(Success Criteria)별 pass/fail을 자동으로 집계하고 리포트를 생성한다. 모든 LLM 호출을 mock하여 OpenAI API 키 없이 테스트를 실행할 수 있으며, `FakeEmbeddings`와 인메모리 ChromaDB로 벡터 DB 의존성도 제거한다.

**How**: parametrize와 mock을 조합하여 테스트를 구성한다.

```python
import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.embeddings import FakeEmbeddings

@pytest.mark.parametrize("model_id,query,expected_intent", [
    ("770S", "E001 에러가 떠요", "troubleshoot"),
    ("770S", "설치 방법 알려줘", "install"),
    ("580", "블루투스 연결이 안 돼요", "connect"),
    ("970S", "체수분 측정 원리가 뭐야?", "clinical"),
    # ... 444개 케이스
])
async def test_intent_classification(model_id, query, expected_intent):
    with patch("app.agents.llm.ChatOpenAI") as mock_llm:
        mock_llm.return_value.ainvoke = AsyncMock(
            return_value=expected_intent
        )
        result = await classify_intent(model_id, query)
        assert result == expected_intent
```

**Trade-offs**: pytest의 플러그인 생태계가 풍부한 만큼 의존성이 많아질 수 있다. 커스텀 플러그인(SCMetricsCollector)의 유지보수 부담도 존재한다. mock 기반 테스트는 실제 LLM 동작을 완벽히 재현하지 못하므로 통합 테스트가 별도로 필요하다.

---

### 2.7 Code Quality

#### Ruff (>=0.8)

**What**: Rust로 작성된 초고속 Python 린터 겸 포매터이다. Black(포매팅) + isort(임포트 정렬) + flake8(린팅)의 기능을 단일 도구로 통합한다.

**Why**: 기존에는 Black(포매팅), isort(임포트 정렬), flake8(린팅)을 각각 설치하고 설정 파일을 개별 관리해야 했다. pyproject.toml에 Black 설정, isort 설정, .flake8 파일을 각각 유지하는 것은 번거롭고 도구 간 충돌(예: Black과 isort의 임포트 스타일 차이)이 발생할 수 있다.

Ruff는 이 세 도구를 하나로 통합하여 `pyproject.toml`의 `[tool.ruff]` 섹션 하나로 모든 설정을 관리한다. Rust로 작성되어 실행 속도가 기존 도구 조합 대비 10~100배 빠르며, pre-commit hook에서의 지연을 최소화한다.

**How**: `pyproject.toml`에서 통합 설정을 관리한다.

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.ruff.format]
quote-style = "double"
```

**Trade-offs**: Ruff는 비교적 신생 도구로, 일부 flake8 플러그인(flake8-docstrings 등)을 아직 완전히 지원하지 않는다. Black과의 미세한 포매팅 차이가 존재할 수 있다.

---

#### Python 3.11+

**What**: Python 3.11은 3.10 대비 10~60% 성능 향상(CPython Faster)과 향상된 에러 메시지를 제공하는 버전이다.

**Why**: Python 3.12를 선택하지 않은 이유는 일부 라이브러리(특히 LangChain 생태계)의 3.12 호환성이 프로젝트 시작 시점에 완전하지 않았기 때문이다. Python 3.10은 모던 타이핑 문법(`str | None`, `list[str]` 등)을 지원하지만 3.11의 성능 개선과 `ExceptionGroup`, 향상된 traceback을 놓치게 된다.

3.11+는 `str | None` union syntax, `TypedDict`, `Literal` 등 모던 타이핑을 활용하여 코드의 가독성과 타입 안전성을 높인다. pydantic-settings와 조합하면 환경변수 바인딩의 타입 검증도 자동화된다.

**How**: 타입 힌트를 적극 활용한다.

```python
from typing import TypedDict, Literal

class AgentState(TypedDict):
    model_id: str | None
    intent: Literal["troubleshoot", "install", "connect", "clinical"] | None
    messages: list[dict[str, str]]
    context: list[str]
    response: str | None
```

**Trade-offs**: Python 3.11은 3.12의 per-interpreter GIL 개선을 사용할 수 없다. 향후 라이브러리 호환성이 안정되면 3.12+ 전환을 고려할 수 있다.

---

#### pydantic-settings

**What**: Pydantic 기반의 설정 관리 라이브러리로, 환경변수를 Python 클래스 필드에 자동 바인딩하고 타입 검증을 수행한다.

**Why**: `python-dotenv` 단독 사용 시 `.env` 파일의 값은 모두 문자열로 로드되므로, 정수/불리언/리스트 등의 타입 변환을 수동으로 처리해야 한다. 또한 필수 환경변수의 누락을 런타임에서야 발견하게 된다. pydantic-settings는 클래스 정의 시점에 타입을 명시하고, 인스턴스 생성 시 자동으로 타입 변환과 검증을 수행한다. 필수 필드가 누락되면 애플리케이션 시작 시점에 `ValidationError`를 발생시켜 조기에 문제를 발견할 수 있다.

중첩 설정(nested settings)도 지원하여 LLM 설정, DB 설정, API 설정을 구조적으로 분리할 수 있다.

**How**: Settings 클래스를 정의하고 환경변수를 자동 바인딩한다.

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    STRUCTURED_DB_URL: str = "sqlite+aiosqlite:///data/inbody.db"
    ROUTER_TEMPERATURE: float = 0.0
    AGENT_TEMPERATURE: float = 0.3
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 200

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

**Trade-offs**: python-dotenv 대비 초기 설정 코드가 많다. 단순한 프로젝트에서는 과한 추상화일 수 있다. Pydantic V2와의 호환성 변경 시 마이그레이션이 필요하다.

---

## 3. 아키텍처 결정 기록 (ADR)

### ADR-001: 결정론적 가드레일 우선, LLM 보조

**Context**: 에이전트가 생성하는 출력의 안전성을 100% 보장해야 한다. 의료 기기인 InBody의 특성상, 잘못된 정보(다른 기종의 에러 해결 방법, 부정확한 임상 데이터)가 제공되면 기기 오작동이나 잘못된 측정 결과로 이어질 수 있다. LLM 기반 검증만으로는 확률적 특성상 100% 보장이 불가능하다.

**Decision**: 가드레일 검증을 3단계로 구성하되, 결정론적 검사를 먼저 수행하고 LLM은 마지막 보조 수단으로만 사용한다.
1. **면책 문구 검증**: 응답에 의료/법적 면책 문구가 포함되었는지 regex로 확인
2. **기종 격리 검증**: 응답에 현재 세션 기종이 아닌 다른 기종의 정보가 포함되었는지 regex로 확인
3. **Level 3 에스컬레이션 검증**: 전문 기술자 개입이 필요한 키워드(하드웨어 교체, 전압 이상 등)가 포함되었는지 확인

결정론적 검사가 모두 통과한 후에만 LLM 기반 최종 검증을 수행한다.

**Rationale**: LLM은 확률적으로 동작하므로 "항상" 올바른 검증을 보장할 수 없다. 결정론적 검사(regex, 문자열 매칭)는 정의된 패턴에 대해 100% 정확하게 동작한다. 결정론적 검사가 hard-fail을 먼저 잡으면 LLM 검증 호출 자체가 불필요해지므로 비용도 절감된다. 이는 "fail-fast" 원칙과 일치한다.

**Consequences**: regex 패턴 작성 시 한국어의 word boundary(`\b`) 이슈가 발생했다. 한국어는 공백 없이 조사가 붙는 교착어이므로 `\b인바디770\b`이 "인바디770의", "인바디770에서" 등을 매칭하지 못했다. 이를 해결하기 위해 word boundary 대신 lookaround 패턴(`(?<=\s|^)인바디770(?=\s|$|[은는이가을를의에서])`)으로 수정했다. 이러한 언어별 특수 패턴은 지속적인 유지보수가 필요하다.

---

### ADR-002: 시멘틱 캐시 의도별 TTL 차등

**Context**: 시멘틱 캐시는 동일하거나 유사한 질문에 대해 LLM 호출 없이 캐시된 응답을 반환하여 비용과 지연 시간을 절감한다. 그러나 캐시 유효 기간(TTL)을 일률적으로 적용하면 정보의 성격에 따른 변경 빈도 차이를 반영하지 못한다. 예를 들어 트러블슈팅 정보(펌웨어 업데이트로 해결 방법이 변경될 수 있음)와 임상 정보(BIA 원리는 거의 변하지 않음)를 같은 TTL로 관리하면, 전자는 오래된 정보를 제공하고 후자는 불필요하게 자주 갱신된다.

**Decision**: 의도(intent)별로 차등 TTL을 적용한다.
| 의도 | TTL | 근거 |
|------|-----|------|
| troubleshoot | 7일 | 펌웨어/소프트웨어 업데이트로 해결 방법이 변경될 수 있음 |
| install | 30일 | 설치 절차는 하드웨어 리비전 변경 시에만 바뀜 |
| connect | 14일 | 연동 앱/프로토콜 업데이트가 간헐적으로 발생 |
| clinical | 90일 | 체성분 분석 원리, 측정 방법론은 거의 불변 |

**Rationale**: 정보의 변경 빈도에 비례하여 TTL을 설정하면 캐시 적중률(hit rate)과 정보 신선도(freshness) 사이의 균형을 최적화할 수 있다. troubleshoot의 짧은 TTL은 최신 펌웨어 기반 해결 방법을 빠르게 반영하고, clinical의 긴 TTL은 불변 정보에 대한 불필요한 LLM 호출을 최대한 줄인다.

**Consequences**: TTL 만료 시 캐시가 삭제되고 다음 동일 질문에서 LLM을 다시 호출하여 캐시를 재생성한다. 이 과정에서 일시적인 캐시 미스(cache miss)가 발생하여 응답 지연이 증가한다. 또한 TTL 값 자체가 경험적 추정에 기반하므로, 실제 운영 데이터를 수집하여 최적 값을 조정해야 한다. 캐시 무효화(invalidation) 로직이 의도별로 분리되어 코드 복잡도가 약간 증가한다.

---

### ADR-003: GPT-4o-mini 전 노드 통일

**Context**: 프로젝트의 LLM 호출 노드는 기종 식별, 의도 분류, 전문 에이전트 응답 생성, 가드레일 검증 등 다수이다. 각 노드의 태스크 복잡도가 다르므로, 노드별로 다른 모델을 사용하는 것이 이론적으로 최적이다. GPT-4o는 복잡한 추론에 강하고, GPT-4o-mini는 단순 분류에 충분하다. 그러나 멀티 모델 구성은 관리 복잡도를 높이고, 비용 예측을 어렵게 만든다.

**Decision**: 모든 노드에 GPT-4o-mini를 통일하여 사용한다.

**Rationale**: 기종 식별과 의도 분류는 본질적으로 분류(classification) 태스크이다. 선택지가 명확하게 정의되어 있고(기종 4개, 의도 4개), 입력 패턴도 예측 가능하므로 GPT-4o-mini로 충분한 정확도를 달성한다. 에이전트 응답 생성은 생성(generation) 태스크이지만, RAG로 검색된 매뉴얼 청크와 Tool Calling으로 조회한 구조화 데이터가 컨텍스트에 이미 포함되어 있으므로, 모델은 "정보 정리"만 수행하면 된다. 이 수준의 정리 작업은 GPT-4o-mini가 잘 처리한다. GPT-4o 대비 약 1/15 비용(입력 토큰 기준)이므로, 전 노드 통일 시 월간 API 비용을 극적으로 절감할 수 있다.

**Consequences**: 복잡한 다단계 추론이 필요한 질문(예: "InBody 770S의 세그먼트별 임피던스 값이 정상 범위를 벗어났을 때 재보정 절차와 관련 에러코드를 함께 알려줘")에서 GPT-4o 대비 품질 저하가 발생할 수 있다. 이를 대비하여 프로젝트 설정(config)에 GPT-4o 구성을 유지해 두었으며, `OPENAI_MODEL` 환경변수 변경만으로 전환할 수 있다. 향후 사용자 피드백을 수집하여 품질 문제가 빈번한 노드만 선택적으로 GPT-4o로 업그레이드하는 단계적 전환도 가능하다.

---

### ADR-004: 3계층 모델 격리

**Context**: InBody 270S, 580, 770S, 970S의 4개 기종은 일부 동일한 에러코드명을 공유하지만 해결 방법이 기종마다 다를 수 있다. 기종 간 정보가 혼선되면 사용자가 잘못된 절차를 수행하여 기기 오작동이나 부정확한 측정 결과가 발생할 수 있다. 단일 계층의 격리 메커니즘은 해당 계층이 실패할 경우 방어가 불가능하다.

**Decision**: 3계층으로 모델 격리를 구현한다.
1. **물리적 격리 (1계층)**: ChromaDB 컬렉션을 기종별로 분리하여 검색 시 해당 기종의 컬렉션에서만 청크를 가져온다.
2. **논리적 격리 (2계층)**: 메타데이터 필터(`model_id` 필드)를 검색 쿼리에 추가하여 혼입된 데이터가 있더라도 필터링한다.
3. **후처리 격리 (3계층)**: 가드레일 노드에서 regex를 사용하여 최종 응답에 현재 세션 기종이 아닌 다른 기종의 고유 키워드가 포함되었는지 검사한다.

**Rationale**: 방어적 프로그래밍(defensive programming)의 "심층 방어(defense in depth)" 원칙을 적용한 것이다. 1계층이 실패하더라도(예: 인제스트 시 잘못된 컬렉션에 저장) 2계층의 메타데이터 필터가 방어한다. 1, 2계층이 모두 실패하더라도(예: 메타데이터가 누락된 문서) 3계층의 regex가 최종 방어선이 된다. 세 계층이 동시에 실패할 확률은 각 계층의 실패 확률의 곱이므로 극히 낮다.

**Consequences**: 컬렉션 4개를 관리하는 오버헤드가 발생한다. 인제스트(데이터 적재) 시 기종별로 올바른 컬렉션에 분리하는 것이 필수이며, 이 과정에서 인적 오류가 가능하다. 인제스트 파이프라인에 기종 검증 단계를 추가하여 이를 방지한다. 3계층 regex의 한국어 패턴 유지보수도 ADR-001에서 언급한 것과 동일한 이슈가 있다. 새로운 기종이 추가되면 세 계층 모두에 해당 기종의 격리 로직을 추가해야 하므로, 확장 시 체크리스트를 문서화해 두었다.

---

## 4. Dev <-> Prod 전환 전략

개발 환경과 프로덕션 환경의 기술 구성 차이 및 전환 방법을 정리한다. 핵심 원칙은 **환경변수와 의존성 그룹 변경만으로 전환**이 가능하도록 설계한 것이다.

| 컴포넌트 | Development | Production | 전환 방법 |
|----------|-------------|------------|-----------|
| Vector DB | ChromaDB (로컬 파일, 임베디드 모드) | Pinecone (매니지드 클라우드) | `pip install .[prod]` + `VECTOR_DB_PROVIDER` 환경변수 변경 |
| Structured DB | SQLite (로컬 파일, aiosqlite) | PostgreSQL (RDS, asyncpg) | `STRUCTURED_DB_URL` 환경변수 변경 |
| LLM | GPT-4o-mini | GPT-4o-mini (또는 GPT-4o) | `OPENAI_MODEL` 환경변수 변경 |
| 컨테이너 | Docker Compose (로컬) | systemd + venv (EC2) | systemd service 파일 배포 |
| SSL | 없음 (localhost) | ALB/Nginx + Let's Encrypt | 리버스 프록시 추가 |

### 전환 상세

**Vector DB 전환**: `pyproject.toml`에 `[project.optional-dependencies]` 섹션으로 prod 의존성 그룹을 정의한다. `pip install .[prod]`를 실행하면 `pinecone-client`가 설치되며, `VECTOR_DB_PROVIDER=pinecone` 환경변수를 설정하면 애플리케이션이 Pinecone 클라이언트를 사용한다. 팩토리 패턴으로 벡터 DB 클라이언트를 생성하므로 애플리케이션 코드 변경이 불필요하다.

```toml
# pyproject.toml
[project.optional-dependencies]
prod = ["pinecone-client>=3.0", "asyncpg>=0.29"]
```

**Structured DB 전환**: SQLAlchemy ORM을 사용하므로 DB URL만 변경하면 PostgreSQL로 전환된다. `STRUCTURED_DB_URL=postgresql+asyncpg://user:pass@rds-endpoint:5432/inbody`로 설정하면 동일한 ORM 코드가 PostgreSQL에서 실행된다. 스키마 마이그레이션은 Alembic을 사용한다.

**LLM 전환**: `OPENAI_MODEL=gpt-4o`로 변경하면 전 노드가 GPT-4o를 사용한다. 노드별 차등 적용이 필요하면 `ROUTER_MODEL`, `AGENT_MODEL` 등 세분화된 환경변수를 추가할 수 있다.

**SSL 전환**: EC2 앞단에 ALB(Application Load Balancer) 또는 Nginx 리버스 프록시를 배치하고, Let's Encrypt 인증서를 적용한다. Docker Compose에 Nginx 서비스를 추가하거나, ALB를 CloudFormation 템플릿에 포함시킨다.

---

> 이 문서는 프로젝트의 기술적 의사결정을 추적하고, 새로운 팀원의 온보딩과 향후 기술 전환 시 참고 자료로 활용하기 위해 작성되었다.
