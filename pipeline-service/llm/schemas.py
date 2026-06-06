"""
JSON Schemas for LLM Structured Output.

These schemas enforce the exact response format from the LLM,
used with LiteLLM's response_format parameter.
"""

# Stage 3: Structure Analysis schema
ANALYZE_SCHEMA = {
    "type": "object",
    "required": ["synopsis", "characters", "locations"],
    "properties": {
        "synopsis": {
            "type": "string",
            "description": "Overall story synopsis (max 200 characters)"
        },
        "characters": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "role"],
                "properties": {
                    "name": {"type": "string", "description": "Standard name"},
                    "aliases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Other names used in the novel"
                    },
                    "role": {
                        "type": "string",
                        "enum": ["protagonist", "supporting", "antagonist", "extra"]
                    },
                    "description": {"type": "string"}
                }
            }
        },
        "locations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type"],
                "properties": {
                    "name": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["indoor", "outdoor", "mixed", "virtual"]
                    },
                    "description": {"type": "string"}
                }
            }
        }
    }
}

# Stage 4: Scene Segmentation schema
SEGMENT_SCHEMA = {
    "type": "object",
    "required": ["scenes"],
    "properties": {
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["location", "time", "type", "description", "text_segment"],
                "properties": {
                    "location": {"type": "string", "description": "Location name or ID"},
                    "time": {
                        "type": "string",
                        "enum": ["day", "night", "dawn", "dusk", "continuous"]
                    },
                    "type": {
                        "type": "string",
                        "enum": ["interior", "exterior"]
                    },
                    "description": {"type": "string"},
                    "text_segment": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                        "description": "[start_offset, end_offset] into chapter text"
                    }
                }
            }
        }
    }
}

# Stage 5: Beat Extraction schema
EXTRACT_SCHEMA = {
    "type": "object",
    "required": ["beats"],
    "properties": {
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "content"],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["action", "dialogue", "transition", "voiceover", "montage"]
                    },
                    "character_id": {
                        "type": ["string", "null"],
                        "description": "Character ID from the global table, null for non-character beats"
                    },
                    "character_text": {
                        "type": ["string", "null"],
                        "description": "Original name as it appears in the novel"
                    },
                    "content": {"type": "string"},
                    "parenthetical": {
                        "type": ["string", "null"],
                        "description": "Acting direction in parentheses"
                    },
                    "emotion": {
                        "type": ["string", "null"],
                        "description": "Emotional state of the character"
                    }
                }
            }
        }
    }
}


# Stage 5b: Critic Agent (HAR-style review) schema
CRITIC_SCHEMA = {
    "type": "object",
    "required": ["corrections"],
    "properties": {
        "corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["beat_id", "issue", "fix"],
                "properties": {
                    "beat_id": {"type": "string"},
                    "issue": {
                        "type": "string",
                        "enum": [
                            "wrong_speaker", "wrong_type", "missing_character",
                            "wrong_content", "duplicate_beat", "should_be_split",
                        ],
                    },
                    "fix": {
                        "type": "object",
                        "required": ["type", "content"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["action", "dialogue", "voiceover", "transition", "montage"]
                            },
                            "character_text": {"type": ["string", "null"]},
                            "content": {"type": "string"},
                            "parenthetical": {"type": ["string", "null"]},
                            "emotion": {"type": ["string", "null"]},
                            "character_id": {"type": ["string", "null"]},
                        }
                    },
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "reasoning": {"type": "string"},
                }
            }
        }
    }
}


# Stage 5c: Refiner Agent — full beats output after applying corrections
REFINER_SCHEMA = {
    "type": "object",
    "required": ["beats"],
    "properties": {
        "beats": {
            "type": "array",
            "description": "Final, definitive beat list after applying critic's corrections.",
            "items": {
                "type": "object",
                "required": ["type", "content"],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["action", "dialogue", "voiceover", "transition", "montage"]
                    },
                    "character_id": {
                        "type": ["string", "null"],
                        "description": "Character ID from the global table, null for non-character beats"
                    },
                    "character_text": {
                        "type": ["string", "null"],
                        "description": "Original name as it appears in the novel"
                    },
                    "content": {"type": "string"},
                    "parenthetical": {
                        "type": ["string", "null"],
                        "description": "Acting direction in parentheses"
                    },
                    "emotion": {
                        "type": ["string", "null"],
                        "description": "Emotional state of the character"
                    }
                }
            }
        }
    }
}
