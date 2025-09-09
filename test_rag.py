from rag import query_rag

question = "Can you about pets at work, please?"
answer = query_rag(question)

print("Q:", question)
print("A:", answer)
