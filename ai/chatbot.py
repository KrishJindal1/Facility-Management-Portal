from ai.knowledge import load_knowledge
from ai.prompts import CHATBOT_SYSTEM_PROMPT
from ai.ollama_client import ask_ai


GREETINGS = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}


def ask_chatbot(question: str):

    question = question.strip()

    # Handle greetings without calling the AI
    if question.lower() in GREETINGS:
        return (
            "Hello! 👋\n\n"
            "Welcome to HomeDesk.\n\n"
            "I can help you with:\n"
            "• Cook services\n"
            "• Driver services\n"
            "• Security Guard services\n"
            "• Pricing estimates\n"
            "• Requirement forms\n"
            "• Booking process\n"
            "• Frequently asked questions\n\n"
            "How can I help you today?"
        )

    knowledge = load_knowledge()

    prompt = f"""
{CHATBOT_SYSTEM_PROMPT}

Knowledge Base

{knowledge}

User Question

{question}
"""

    return ask_ai(prompt)