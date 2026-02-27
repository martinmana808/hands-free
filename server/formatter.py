# Formatting Logic for Dictated Text

def format_text(raw_text: str, style: str) -> str:
    """
    Takes raw transcription and applies formatting rules based on the style.
    Styles: "professional", "slack", "casual"
    """
    text = raw_text.strip()
    
    if not text:
        return ""

    if style == "professional":
        # Basic: Capitalize first letter, ensure it ends with punctuation
        text = text[0].upper() + text[1:]
        if text[-1] not in ['.', '!', '?']:
            text += '.'
        return text
        
    elif style == "slack":
        # Basic: keep it lowercase, maybe add an emoji if it sounds like a greeting
        text = text.lower()
        if "hello" in text or "hi" in text:
            text += " 👋"
        return text
        
    elif style == "casual":
        # Basic: just return as is, maybe strip some filler words (mock)
        return text

    # Default fallback
    return text
