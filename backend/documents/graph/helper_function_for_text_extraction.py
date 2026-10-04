


def extract_text(content) -> str:

    """
    Only useable in case of Groq API because every model has it's own way to give response
    """

    """Normalize message content across providers — some return a plain string,
    others return a list of content blocks (e.g. [{'type': 'text', 'text': '...'}])."""
    
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get('text', ''))
            elif isinstance(block, str):
                parts.append(block)
        return ''.join(parts)
    return str(content)