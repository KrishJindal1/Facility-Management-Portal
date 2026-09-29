from ai.knowledge import load_knowledge
from ai.prompts import CHATBOT_SYSTEM_PROMPT
from ai.providers import get_ai_provider


GREETINGS = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}


def ask_chatbot(question: str) -> str:
    question = (question or "").strip()
    if not question:
        return "Please ask a question about HomeDesk facility services."

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

    try:
        knowledge = load_knowledge()
    except Exception:
        knowledge = "HomeDesk provides verified cook, driver, and security guard services."

    system_instruction = f"{CHATBOT_SYSTEM_PROMPT}\n\nKnowledge Base:\n{knowledge}"
    provider = get_ai_provider()
    return provider.ask(prompt=question, system_prompt=system_instruction)