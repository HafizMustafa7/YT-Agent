"""
Prompt loader — loads system prompt and few-shot examples for story generation.

Usage:
    from app.core_yt.prompts.loader import load_system_prompt, load_examples
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent
EXAMPLES_DIR = PROMPTS_DIR / "examples"


def load_bible_system_prompt() -> str:
    """
    Load the system prompt specifically designed for generating the internal Story Bible.
    """
    path = PROMPTS_DIR / "bible_system_prompt.txt"
    if not path.exists():
        raise FileNotFoundError(f"Bible system prompt not found: {path}. Ensure it exists.")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        raise ValueError("bible_system_prompt.txt is empty.")
    logger.debug("Bible system prompt loaded (%d chars).", len(content))
    return content


def load_system_prompt() -> str:
    """
    Load the system prompt from system_prompt.txt.

    Raises:
        FileNotFoundError: if system_prompt.txt is missing (hard failure —
            story generation cannot proceed without a system prompt).
    """
    system_prompt_path = PROMPTS_DIR / "system_prompt.txt"
    if not system_prompt_path.exists():
        raise FileNotFoundError(
            f"System prompt not found at: {system_prompt_path}. "
            "Ensure system_prompt.txt exists in the prompts directory."
        )
    with open(system_prompt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        raise ValueError("system_prompt.txt is empty.")
    logger.debug("System prompt loaded (%d chars).", len(content))
    return content


def load_examples() -> list:
    """
    Load all example JSON files from the examples/ subdirectory.

    Each file is expected to follow the structure:
        {
          "label": str,
          "description": str,
          "input": { ... },
          "frame_structure": { ... },
          "output": { topic, total_duration, pacing, full_story, frames[] }
        }

    Only the "output" block is extracted for LLM reference — the full
    file structure (label, description, input, frame_structure) is
    included as context so the LLM understands the relationship between
    input and output.

    Returns:
        List of example dicts. Empty list if examples/ does not exist
        or contains no valid JSON files (soft failure — examples are
        optional few-shot context).
    """
    examples = []

    if not EXAMPLES_DIR.exists():
        logger.warning("Examples directory not found: %s", EXAMPLES_DIR)
        return examples

    for file in sorted(EXAMPLES_DIR.glob("*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate expected structure
            if not isinstance(data, dict):
                logger.warning("Skipping %s — not a JSON object.", file.name)
                continue

            if "output" not in data:
                logger.warning(
                    "Skipping %s — missing 'output' key.", file.name
                )
                continue

            examples.append({
                "label": data.get("label", file.stem),
                "description": data.get("description", ""),
                "input": data.get("input", {}),
                "frame_structure": data.get("frame_structure", {}),
                "output": data["output"],
            })
            logger.debug("Loaded example: %s", file.name)

        except json.JSONDecodeError as e:
            logger.warning(
                "Skipping %s — invalid JSON: %s", file.name, e
            )
        except OSError as e:
            logger.warning(
                "Skipping %s — could not read file: %s", file.name, e
            )

    logger.info("Loaded %d example(s) from %s.", len(examples), EXAMPLES_DIR)
    return examples
