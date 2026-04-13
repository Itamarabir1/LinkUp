from enum import Enum


class DispatchTarget(str, Enum):
    """Possible targets for event dispatch — domain level."""

    RABBITMQ = "RABBITMQ"
    KAFKA = "KAFKA"
    WEBHOOK = "WEBHOOK"
    WEBSOCKET = "WEBSOCKET"
    REDIS = "REDIS"
