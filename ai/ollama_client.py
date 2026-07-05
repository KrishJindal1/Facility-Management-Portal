import ollama

MODEL = "llama3.1:8b"


def ask_ai(prompt: str) -> str:
    """
    Sends a prompt to the local Ollama model and returns the response.
    """

    try:

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response["message"]["content"]

    except Exception as e:

        return f"Error communicating with AI: {str(e)}"