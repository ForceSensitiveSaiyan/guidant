from fastapi import FastAPI
from pydantic import BaseModel
from rag import query_rag

app = FastAPI()


class Query(BaseModel):
    question: str


@app.post("/ask")
async def ask(query: Query):
    result = query_rag(query.question)
    return {"answer": result["result"]}
