from functools import lru_cache
import json
from config import KNOWLEDGE_DIR



def load_text_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_knowledge():
    """
    Loads all knowledge files from the knowledge directory.
    The result is cached so files are read only once.
    """

    knowledge = []

    if not KNOWLEDGE_DIR.exists():
        raise FileNotFoundError(f"Knowledge directory not found: {KNOWLEDGE_DIR}")

    for file in sorted(KNOWLEDGE_DIR.iterdir()):

        if file.suffix == ".txt":

            knowledge.append(load_text_file(file))

        elif file.suffix == ".json":

            data = load_json_file(file)

            knowledge.append(f"\n{file.stem.upper()}\n")

            knowledge.append(
                json.dumps(
                    data,
                    indent=4,
                    ensure_ascii=False
                )
            )
   
    return "\n\n".join(knowledge)