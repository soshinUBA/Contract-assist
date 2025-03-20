import os
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import spacy
import re
import random
import string
from typing import Dict, Tuple, List, Set
import logging
import json
from openai import OpenAI
from helpers import get_model
from prompt_loader import PROMPT_MANAGER

load_dotenv()

class EntityAnonymizer:
    """A class to detect, validate with LLM, and anonymize entities in text."""

    def __init__(self):
        """
        Initialize the EntityAnonymizer with necessary models and OpenAI client.
        """
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Initialize OpenAI client
        self.openai_api_key = os.getenv("openai-api-key")
        self.client = get_model()

        # Load NLP models
        self.logger.info("Loading NLP models...")
        self._load_models()

        # Initialize mapping storage
        self.entity_mapping: Dict[str, str] = {}
        self.used_dummy_values: Dict[str, set] = {
            'PERSON': set(),
            'ORG': set(),
            'EMAIL': set(),
            'PHONE': set()
        }

        # Initialize dummy name components
        self._initialize_dummy_names()

    def _validate_entities_with_llm(self, entities: List[dict]) -> Dict[str, List[str]]:
        """
        Validate extracted entities using LLM to confirm if they are valid person/organization names.

        Args:
            entities (List[dict]): List of extracted entities

        Returns:
            Dict[str, List[str]]: Dictionary with validated entities grouped by type
        """
        # Group unique entities by type
        unique_persons = {e['text'] for e in entities if e['label'] == 'PERSON'}
        unique_orgs = {e['text'] for e in entities if e['label'] == 'ORG'}

        validated_entities = {'PERSON': [], 'ORG': []}

        # Validate person names
        if unique_persons:
            person_prompt = self._create_validation_prompt("PERSON", unique_persons)
            validated_persons = self._get_llm_validation(person_prompt)
            validated_entities['PERSON'] = validated_persons

        # Validate organization names
        if unique_orgs:
            org_prompt = self._create_validation_prompt("ORG", unique_orgs)
            validated_orgs = self._get_llm_validation(org_prompt)
            validated_entities['ORG'] = validated_orgs

        return validated_entities

    def _create_validation_prompt(self, entity_type: str, entities: Set[str]) -> str:
        """Create prompt for LLM validation."""
        entity_list = "\n".join([f"- {entity}" for entity in entities])

        if entity_type == "PERSON":
            prompt = PROMPT_MANAGER.get_prompt('CREATE_VALIDATION_PROMOPT', 'person_prompt', entity_list=entity_list)

        else:  # ORG
            prompt = PROMPT_MANAGER.get_prompt('CREATE_VALIDATION_PROMOPT', 'org_prompt', entity_list=entity_list)

        return prompt

    def _get_llm_validation(self, prompt: str) -> List[str]:
        """
        Get validation results from LLM.

        Args:
            prompt (str): Validation prompt for LLM

        Returns:
            List[str]: List of validated entity names
        """
        try:
            response = self.client.invoke(
                input=[
                    {"role": "system",
                     "content": "You are a helpful assistant that validates entity names. Respond only with a JSON object containing a 'valid_names' array."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            # Parse the JSON response
            json_str = response.content
            parsed_response = json.loads(json_str)
            return parsed_response.get('valid_names', [])

        except Exception as e:
            self.logger.error(f"Error in LLM validation: {str(e)}")
            return []

    # Rest of the class remains unchanged except for the corrected JSON handling

    def anonymize_text(self, text: str) -> Tuple[str, Dict[str, str], Dict[str, List[str]]]:
        """
        Anonymize entities in the given text after LLM validation.

        Args:
            text (str): The input text to be anonymized

        Returns:
            Tuple[str, Dict[str, str], Dict[str, List[str]]]: A tuple containing:
                - The anonymized text
                - A dictionary mapping original entities to their dummy values
                - A dictionary of validated entities by type
        """
        try:
            # Extract initial entities
            initial_entities = self._extract_entities(text)

            # Validate entities with LLM
            validated_entities = self._validate_entities_with_llm(initial_entities)

            # Create set of validated entities for quick lookup
            valid_persons = set(validated_entities['PERSON'])
            valid_orgs = set(validated_entities['ORG'])

            # Filter entities and create final list
            final_entities = []
            for entity in initial_entities:
                if (entity['label'] == 'PERSON' and entity['text'] in valid_persons) or \
                        (entity['label'] == 'ORG' and entity['text'] in valid_orgs) or \
                        entity['label'] in ['EMAIL', 'PHONE']:
                    self._add_entity(final_entities, entity['text'], entity['label'],
                                     entity['start'], entity['end'])

            # Add phone numbers
            phone_entities = self._extract_phone_numbers(text)
            for phone in phone_entities:
                self._add_entity(final_entities, phone["text"], "PHONE",
                                 phone["start"], phone["end"])

            # Create anonymized text
            anonymized = self._apply_mappings(text, final_entities)

            return anonymized, self.entity_mapping, validated_entities

        except Exception as e:
            self.logger.error(f"Error during text anonymization: {str(e)}")
            raise

    # The rest of the methods remain unchanged as previously provided

    def _load_models(self) -> None:
        """Load required NLP models."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                "xlm-roberta-large-finetuned-conll03-english"
            )
            self.model = AutoModelForTokenClassification.from_pretrained(
                "xlm-roberta-large-finetuned-conll03-english"
            )
            self.nlp = pipeline("ner", model=self.model, tokenizer=self.tokenizer,
                                aggregation_strategy="simple")
            self.sent_nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            self.logger.error(f"Error loading models: {str(e)}")
            raise

    def _initialize_dummy_names(self) -> None:
        """Initialize components for generating dummy names."""
        self.dummy_components = {
            'PERSON': {
                'first_names': [
                    "John", "Jane", "Michael", "Sarah", "David", "Emma",
                    "Robert", "Lisa", "William", "Mary", "James", "Elizabeth",
                    "Richard", "Patricia", "Thomas", "Jennifer"
                ],
                'last_names': [
                    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
                    "Miller", "Davis", "Anderson", "Wilson", "Taylor", "Moore",
                    "Martin", "Lee", "Thompson", "White"
                ],
                'single_names': [
                    "Anderson", "Brooks", "Carter", "Douglas", "Edwards", "Foster",
                    "Greene", "Hayes", "Irving", "Jenkins", "Kennedy", "Lynch",
                    "Mitchell", "Newman", "Pearson", "Quinn", "Rogers", "Stevens",
                    "Turner", "Walsh", "Young", "Abbott", "Baker", "Cooper"
                ]
            },
            'ORG': {
                'prefixes': [
                    "Alpha", "Beta", "Global", "Tech", "Prime", "Nova", "Delta",
                    "Summit", "Vertex", "Quantum", "Nexus", "Phoenix", "Stellar",
                    "Atlas", "Omega", "Unity"
                ],
                'suffixes': [
                    "Corp", "Inc", "Ltd", "Systems", "Solutions", "Group",
                    "Industries", "Dynamics", "Technologies", "International",
                    "Enterprises", "Partners", "Associates", "Holdings"
                ],
                'single_names': [
                    "Acme", "Apex", "Catalyst", "Dynamics", "Eclipse", "Fusion",
                    "Genesis", "Horizon", "Innovate", "Kinetic", "Lambda", "Matrix",
                    "Nexus", "Orbit", "Pinnacle", "Quantum", "Radiant", "Synergy",
                    "Titan", "Unified", "Vertex", "Zenith", "Blueprint", "Cipher"
                ]
            }
        }

    def _generate_unique_dummy_name(self, original_text: str, entity_type: str) -> str:
        """Generate a unique dummy name for an entity."""
        words = original_text.split()
        max_attempts = 100

        for _ in range(max_attempts):
            if entity_type == "PERSON":
                if len(words) == 1:
                    dummy = random.choice(self.dummy_components['PERSON']['single_names'])
                else:
                    dummy = (f"{random.choice(self.dummy_components['PERSON']['first_names'])} "
                             f"{random.choice(self.dummy_components['PERSON']['last_names'])}")

            elif entity_type == "ORG":
                if len(words) == 1:
                    dummy = random.choice(self.dummy_components['ORG']['single_names'])
                else:
                    dummy = (f"{random.choice(self.dummy_components['ORG']['prefixes'])} "
                             f"{random.choice(self.dummy_components['ORG']['suffixes'])}")

            elif entity_type == "EMAIL":
                username = ''.join(random.choices(string.ascii_lowercase, k=8))
                domains = ["example.com", "dummy.com", "test.net", "sample.org"]
                dummy = f"{username}@{random.choice(domains)}"

            elif entity_type == "PHONE":
                area_codes = ["555"]  # Using 555 to ensure fake numbers
                dummy = f"({random.choice(area_codes)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"

            # Check if dummy value is unique
            if dummy not in self.used_dummy_values[entity_type]:
                self.used_dummy_values[entity_type].add(dummy)
                return dummy

        raise ValueError(f"Could not generate unique dummy value after {max_attempts} attempts")

    def _extract_phone_numbers(self, text: str) -> List[dict]:
        """Extract phone numbers from text for multiple countries including US, Germany, Portugal, China, and Japan.

        Formats supported:
        US: +1 XXX-XXX-XXXX, (XXX) XXX-XXXX, XXX-XXX-XXXX
        Germany: +49 XXX XXXXXXX, +49-XXX-XXXXXXX, 0XXX-XXXXXXX
        Portugal: +351 XXX XXX XXX, +351-XXX-XXX-XXX
        China: +86 XXX XXXX XXXX, +86-XXX-XXXX-XXXX
        Japan: +81 XX XXXX XXXX, +81-XX-XXXX-XXXX
        """
        phone_patterns = [
            # US Patterns
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',  # (123) 456-7890
            r'\+1[-.\s]?\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # +1-123-456-7890

            # German Patterns
            r'\+49[-.\s]?\d{3}[-.\s]?\d{7}\b',  # +49 123 4567890
            r'0\d{3}[-.\s]?\d{7}\b',  # 0123 4567890
            r'\+49[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b',  # +49 1234 5678 9012 (mobile)
            r'\+49[-.\s]?\d{2}[-.\s]?\d{4}[-.\s]?\d{4}\b',

            # Portuguese Patterns
            r'\+351[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{3}\b',  # +351 123 456 789
            r'00351[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{3}\b',  # 00351 123 456 789

            # Chinese Patterns
            r'\+86[-.\s]?\d{3}[-.\s]?\d{4}[-.\s]?\d{4}\b',  # +86 123 4567 8901
            r'00886[-.\s]?\d{3}[-.\s]?\d{4}[-.\s]?\d{4}\b',  # 00886 123 4567 8901

            # Japanese Patterns
            r'\+81[-.\s]?\d{2}[-.\s]?\d{4}[-.\s]?\d{4}\b',  # +81 12 3456 7890
            r'0\d{1,2}[-.\s]?\d{4}[-.\s]?\d{4}\b',  # 012-3456-7890 or 0123-456-7890
        ]

        def identify_country(phone_number: str) -> str:
            """Identify the country based on the phone number pattern."""
            if phone_number.startswith('+1') or len(
                    phone_number.replace('-', '').replace('.', '').replace(' ', '')) == 10:
                return "US"
            elif '+49' in phone_number or phone_number.startswith('0'):
                return "GERMANY"
            elif '+351' in phone_number or '00351' in phone_number:
                return "PORTUGAL"
            elif '+86' in phone_number or '00886' in phone_number:
                return "CHINA"
            elif '+81' in phone_number or (phone_number.startswith('0') and len(phone_number) >= 10):
                return "JAPAN"
            return "UNKNOWN"

        phone_entities = []
        for pattern in phone_patterns:
            for match in re.finditer(pattern, text):
                phone_number = match.group()
                country = identify_country(phone_number)
                phone_entities.append({
                    "text": phone_number,
                    "start": match.start(),
                    "end": match.end(),
                    "label": "PHONE",
                    "country": country
                })

        return phone_entities

    def _extract_entities(self, text: str) -> List[dict]:
        """Extract entities from text and create mappings."""
        entities = []
        doc = self.sent_nlp(text)

        # Process named entities
        for sent in doc.sents:
            ner_results = self.nlp(sent.text)

            for entity in ner_results:
                if entity['entity_group'] in ['PER', 'ORG']:
                    if entity.get('score', 1.0) < 0.85:
                        continue

                    entity_text = entity['word'].strip(" #")
                    if not entity_text or len(entity_text) < 2 or '#' in entity_text:
                        continue

                    if entity['entity_group'] == 'ORG' and (
                            "monotype" in entity_text.lower() or
                            "font software" in entity_text.lower()
                    ):
                        continue

                    label = 'PERSON' if entity['entity_group'] == 'PER' else 'ORG'
                    entities.append({
                        "text": entity_text,
                        "start": sent.start_char + entity['start'],
                        "end": sent.start_char + entity['end'],
                        "label": label
                    })

        # Process emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            email = match.group()
            if '@monotype.com' not in email.lower():
                entities.append({
                    "text": email,
                    "start": match.start(),
                    "end": match.end(),
                    "label": "EMAIL"
                })

        return self._remove_duplicates(entities)

    def _add_entity(self, entities: List[dict], text: str, label: str,
                    start: int, end: int) -> None:
        """Add an entity to the entities list and create mapping if needed."""
        if text not in self.entity_mapping:
            self.entity_mapping[text] = self._generate_unique_dummy_name(text, label)

        entities.append({
            "text": text,
            "dummy_value": self.entity_mapping[text],
            "start": start,
            "end": end,
            "label": label
        })

    def _remove_duplicates(self, entities: List[dict]) -> List[dict]:
        """Remove duplicate entities while preserving order."""
        seen = set()
        unique_entities = []

        for entity in entities:
            identifier = (entity['start'], entity['end'], entity['label'])
            if identifier not in seen:
                seen.add(identifier)
                unique_entities.append(entity)

        return unique_entities

    def _apply_mappings(self, text: str, entities: List[dict]) -> str:
        """Replace all instances of detected entities, even when mixed with special characters."""
        modified_text = text

        # Convert entity mapping into a dictionary
        entity_replacements = {entity['text']: entity['dummy_value'] for entity in entities}

        # Sort entity names from longest to shortest to avoid partial replacements
        sorted_entities = sorted(entity_replacements.keys(), key=len, reverse=True)

        for original_text in sorted_entities:
            dummy_value = entity_replacements[original_text]

            # New regex pattern: match the entity even if attached to special characters
            # pattern = rf'(\W|^){re.escape(original_text)}(\W|$)'

            # Replace all occurrences in the text, keeping surrounding characters unchanged
            # modified_text = re.sub(pattern, rf'\1{dummy_value}\2', modified_text)
            
            modified_text = modified_text.replace(original_text, dummy_value,)
 
        return modified_text
        
    
    def clear_mappings(self) -> None:
        """Clear all stored mappings and used dummy values."""
        self.entity_mapping.clear()
        for entity_type in self.used_dummy_values:
            self.used_dummy_values[entity_type].clear()


# Example usage
# if __name__ == "__main__":
#     # File path
#     file_path = "contract_b4.txt"

#     # Read the original text
#     with open(file_path, "r", encoding="utf-8") as file:
#         txt = file.read()

#     # Initialize anonymizer
#     anonymizer = EntityAnonymizer()

#     try:
#         # Anonymize text
#         anonymized_text, mapping, validated_entities = anonymizer.anonymize_text(txt)

#         print("Original Text:")
#         print(txt)

#         print("\nValidated Entities:")
#         print("Persons:", validated_entities['PERSON'])
#         print("Organizations:", validated_entities['ORG'])

#         print("\nAnonymized Text:")
#         print(anonymized_text)

#         print("\nMapping Dictionary:")
#         for original, dummy in mapping.items():
#             print(f"{original} → {dummy}")

#         # Generate the anonymized file path
#         base, ext = os.path.splitext(file_path)
#         anonymized_file_path = f"{base}_anonymized{ext}"

#         # Save the anonymized text
#         with open(anonymized_file_path, "w", encoding="utf-8") as file:
#             file.write(anonymized_text)

#         print(f"\nAnonymized text saved at: {anonymized_file_path}")

#     except Exception as e:
#         print(f"Error during anonymization: {str(e)}")