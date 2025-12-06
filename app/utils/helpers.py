"""
Helper Utilities
General utility functions
"""

from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, date
import json


def generate_uuid() -> str:
    """Generate UUID string"""
    return str(uuid.uuid4())


def current_timestamp() -> datetime:
    """Get current timestamp"""
    return datetime.now()


def dict_to_json(data: Dict) -> str:
    """Convert dict to JSON string"""
    return json.dumps(data, default=str)


def json_to_dict(json_str: str) -> Dict:
    """Convert JSON string to dict"""
    return json.loads(json_str)


def chunks(lst: List, n: int):
    """Yield successive n-sized chunks from list"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default value"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except:
        return default


def remove_none_values(data: Dict) -> Dict:
    """Remove keys with None values from dict"""
    return {k: v for k, v in data.items() if v is not None}


def merge_dicts(*dicts: Dict) -> Dict:
    """Merge multiple dictionaries"""
    result = {}
    for d in dicts:
        result.update(d)
    return result
