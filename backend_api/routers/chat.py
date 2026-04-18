import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend_api.provider import normalize_provider, select_model_for_provider
from backend_api.schemas import ChatQueryRequest, ChatQueryResponse
from backend_api.state import app_state

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/query", response_model=ChatQueryResponse)
def chat_query(payload: ChatQueryRequest) -> ChatQueryResponse:
    rag = app_state.get_rag_engine()
    if rag is None or rag.vector_store is None:
        raise HTTPException(status_code=400, detail="RAG engine not ready")

    if not rag.all_chunks:
        raise HTTPException(status_code=400, detail="No indexed resume found. Parse a resume first")

    try:
        answer = ""
        context = ""
        prompt = ""

        normalized_provider = normalize_provider(payload.provider)
        selected_model = select_model_for_provider(normalized_provider, payload.model)

        for streamed_answer, streamed_context, streamed_prompt in rag.query(
            payload.message,
            provider=normalized_provider,
            model=selected_model,
            think=payload.think,
        ):
            answer = streamed_answer
            context = streamed_context
            prompt = streamed_prompt

        return ChatQueryResponse(answer=answer, context=context, prompt=prompt, chunks=rag.all_chunks)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/query/stream")
def chat_query_stream(payload: ChatQueryRequest) -> StreamingResponse:
    rag = app_state.get_rag_engine()
    if rag is None or rag.vector_store is None:
        raise HTTPException(status_code=400, detail="RAG engine not ready")

    if not rag.all_chunks:
        raise HTTPException(status_code=400, detail="No indexed resume found. Parse a resume first")

    normalized_provider = normalize_provider(payload.provider)
    selected_model = select_model_for_provider(normalized_provider, payload.model)

    def generate():
        try:
            context = ""
            prompt = ""
            answer = ""

            for streamed_answer, streamed_context, streamed_prompt in rag.query(
                payload.message,
                provider=normalized_provider,
                model=selected_model,
                think=payload.think,
            ):
                answer = streamed_answer
                context = streamed_context
                prompt = streamed_prompt
                yield json.dumps({"type": "chunk", "answer": answer}) + "\n"

            yield json.dumps(
                {
                    "type": "done",
                    "answer": answer,
                    "context": context,
                    "prompt": prompt,
                    "chunks": rag.all_chunks,
                }
            ) + "\n"
        except Exception as exc:
            yield json.dumps({"type": "error", "detail": str(exc)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
