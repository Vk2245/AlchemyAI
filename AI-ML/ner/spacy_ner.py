"""
NER Entity Extraction Module using spaCy / Hugging Face & Regex.

Extracts standard business entities (PERSON, ORG, DATE, MONEY) and 
custom entities (INVOICE_NUMBER, PO_NUMBER, GSTIN) from document text.
"""
import re
from typing import List, Dict, Any

try:
    import spacy
except ImportError:
    spacy = None

# Optional HF transformers import
try:
    from transformers import pipeline
except ImportError:
    pipeline = None

from extraction.schema_models import ExtractedEntity


class DocumentNER:
    def __init__(self, use_spacy: bool = True, spacy_model: str = "en_core_web_sm"):
        self.nlp = None
        self.hf_ner = None
        
        if use_spacy and spacy:
            try:
                self.nlp = spacy.load(spacy_model)
            except OSError:
                print(f"Warning: spaCy model '{spacy_model}' not found. Downloading...")
                import spacy.cli
                spacy.cli.download(spacy_model)
                self.nlp = spacy.load(spacy_model)
        elif not use_spacy and pipeline:
            # Fallback to HF Transformers
            self.hf_ner = pipeline("ner", aggregation_strategy="simple")
            
        # Regex patterns for business documents
        self.patterns = {
            "INVOICE_NUMBER": r"(?i)(?:inv|invoice)\s*(?:no\.?|num\.?|number|#)?\s*[:\-]?\s*([A-Z0-9\-\/]{4,15})",
            "PO_NUMBER": r"(?i)(?:po|purchase\s*order)\s*(?:no\.?|num\.?|number|#)?\s*[:\-]?\s*([A-Z0-9\-\/]{4,15})",
            "GSTIN": r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}",
            "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "PHONE": r"(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}"
        }

    def extract_regex(self, text: str) -> List[ExtractedEntity]:
        entities = []
        for entity_type, pattern in self.patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entities.append(ExtractedEntity(
                    entity_type=entity_type,
                    value=match.group(1) if len(match.groups()) > 0 else match.group(0),
                    source_text=match.group(0),
                    confidence=0.95,  # High confidence for regex matches
                    human_verified=False
                ))
        return entities

    def extract_nlp(self, text: str) -> List[ExtractedEntity]:
        entities = []
        # Mapping spacy entity types to our schema
        type_mapping = {
            "PERSON": "PERSON",
            "ORG": "ORG",
            "GPE": "GPE",
            "DATE": "DATE",
            "MONEY": "MONEY",
            "FAC": "ORG",
            "LOC": "GPE"
        }
        
        if self.nlp:
            # Using spaCy
            # Text chunking if too long
            if len(text) > 100000:
                text = text[:100000]
                
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in type_mapping:
                    entities.append(ExtractedEntity(
                        entity_type=type_mapping[ent.label_],
                        value=ent.text.strip(),
                        source_text=ent.text,
                        confidence=0.85, # Base confidence for spaCy
                        human_verified=False
                    ))
        elif self.hf_ner:
            # Using Hugging Face
            results = self.hf_ner(text[:2000]) # HF context limit constraint
            for res in results:
                ent_group = res.get("entity_group", "")
                if ent_group in type_mapping:
                    entities.append(ExtractedEntity(
                        entity_type=type_mapping[ent_group],
                        value=res.get("word", "").strip(),
                        source_text=res.get("word", ""),
                        confidence=float(res.get("score", 0.8)),
                        human_verified=False
                    ))
                    
        return entities

    def extract_all(self, text: str) -> List[ExtractedEntity]:
        regex_ents = self.extract_regex(text)
        nlp_ents = self.extract_nlp(text)
        
        # Merge and deduplicate simple overlaps
        all_ents = regex_ents + nlp_ents
        
        # Basic deduplication by value and type
        unique_ents = {}
        for ent in all_ents:
            key = f"{ent.entity_type}_{ent.value.lower()}"
            if key not in unique_ents or ent.confidence > unique_ents[key].confidence:
                unique_ents[key] = ent
                
        return list(unique_ents.values())

# Singleton instance for pipeline use
_ner_engine = None

def get_ner_engine():
    global _ner_engine
    if _ner_engine is None:
        _ner_engine = DocumentNER()
    return _ner_engine

def run_ner_extraction(text: str) -> List[ExtractedEntity]:
    """Helper to run NER extraction quickly."""
    if not text.strip():
        return []
    engine = get_ner_engine()
    return engine.extract_all(text)
