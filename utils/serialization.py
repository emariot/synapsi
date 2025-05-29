import orjson
from datetime import datetime
import numpy as np
from decimal import Decimal

def orjson_dumps(obj, *, default=None):
    """
    Serializa objetos para JSON usando orjson com tratamento de tipos personalizados.
    
    Args:
        obj: Objeto a ser serializado.
        default: Função padrão para tipos não serializáveis (opcional).
    
    Returns:
        bytes: JSON serializado como bytes.
    """
    def _default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, Decimal):
            return float(obj)
        if default:
            return default(obj)
        raise TypeError(f"Tipo não serializável: {type(obj)}")

    return orjson.dumps(obj, default=_default)

def orjson_loads(data):
    """
    Desserializa JSON usando orjson.
    
    Args:
        data: String ou bytes contendo JSON.
    
    Returns:
        Objeto Python desserializado.
    """
    return orjson.loads(data)