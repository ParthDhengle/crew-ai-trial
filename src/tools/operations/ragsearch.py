def rag_search(query: str, top_k: int = 5) -> tuple[bool, str]:
    # Integrates rag_tool
    from ..rag_tool import RagTool
    tool = RagTool()
    return True, tool._run(query, top_k)  # Delegate