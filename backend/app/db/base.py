try:
    from sqlalchemy.orm import DeclarativeBase
    from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
    class Base(DeclarativeBase):
        pass
except ImportError:
    class Base:
        metadata = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    def Column(*args, **kwargs):
        return None
    def String(*args, **kwargs):
        return None
    def Integer(*args, **kwargs):
        return None
    def Float(*args, **kwargs):
        return None
    def Boolean(*args, **kwargs):
        return None
    def DateTime(*args, **kwargs):
        return None
    def ForeignKey(*args, **kwargs):
        return None
    def Text(*args, **kwargs):
        return None
    def JSON(*args, **kwargs):
        return None
