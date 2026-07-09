import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class OutputEvaluator:
    """Evaluates and cleans responses without modifying business data."""

    def evaluate(self, response: Any) -> Any:
        logger.debug("OutputEvaluator started.")

        applied_rules = []

        if isinstance(response, str):
            cleaned_text, rules = self._clean_text(response)
            applied_rules.extend(rules)
            result = cleaned_text
        elif isinstance(response, dict):
            result = response.copy()
            if "assistant_message" in result and isinstance(result["assistant_message"], str):
                cleaned_text, rules = self._clean_text(result["assistant_message"])
                applied_rules.extend(rules)
                result["assistant_message"] = cleaned_text
        else:
            result = response

        if applied_rules:
            logger.debug("Rule applied:")
            for rule in applied_rules:
                logger.debug(f"- {rule}")

        logger.debug("OutputEvaluator completed.")
        return result

    def _clean_text(self, text: str) -> tuple[str, list[str]]:
        applied_rules = []

        # Rule 6: Convert unexpected exceptions into friendly responses
        exception_keywords = [
            "ApplicationException",
            "RepositoryException",
            "Traceback",
            "Stack Trace",
            "Internal Error",
        ]
        if any(keyword in text for keyword in exception_keywords):
            applied_rules.append("Converted exception to friendly response")
            return "Sorry, I couldn't process your request.\nPlease try again.", applied_rules

        original_text = text

        # Rule 1: Remove markdown fences
        if "```" in text:
            # We want to remove the markdown fences entirely
            text = re.sub(r"```(?:[a-zA-Z]*)\n?", "", text)
            text = re.sub(r"```", "", text)
            if text != original_text:
                applied_rules.append("Removed markdown")
                original_text = text

        # Rule 2: Remove accidental JSON leakage
        if "{" in text and '"intent"' in text:
            text = re.sub(r'\{\s*"intent"\s*:.*?\}', "", text, flags=re.DOTALL)
            if text != original_text:
                applied_rules.append("Removed accidental JSON leakage")
                original_text = text

        # Rule 3: Remove duplicate paragraphs
        paragraphs = text.split("\n")
        seen = set()
        unique_paragraphs = []
        has_duplicates = False
        for p in paragraphs:
            stripped = p.strip()
            if stripped:
                if stripped not in seen:
                    seen.add(stripped)
                    unique_paragraphs.append(p)
                else:
                    has_duplicates = True
            else:
                unique_paragraphs.append(p)

        if has_duplicates:
            text = "\n".join(unique_paragraphs)
            applied_rules.append("Removed duplicate paragraph")
            original_text = text

        # Rule 4: Remove generic endings
        generic_endings = [
            "Is there anything else I can help you with?",
            "Would you like additional details?",
            "Would you like more information?",
            "How may I assist you today?",
            "Please let me know if you need anything else.",
        ]
        has_generic_endings = False
        for ending in generic_endings:
            if ending in text:
                text = text.replace(ending, "")
                has_generic_endings = True

        if has_generic_endings:
            applied_rules.append("Removed generic ending")
            original_text = text

        # Rule 5: Normalize whitespace
        new_text = "\n".join(line.rstrip() for line in text.split("\n"))
        new_text = re.sub(r"\n{3,}", "\n\n", new_text)
        new_text = new_text.strip()
        if new_text != text:
            applied_rules.append("Normalized whitespace")
            text = new_text

        return text, applied_rules
