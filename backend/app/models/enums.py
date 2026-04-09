import enum


class TopicStatus(enum.StrEnum):
    active = "active"
    closed = "closed"
    archived = "archived"


class MemberRole(enum.StrEnum):
    creator = "creator"
    admin = "admin"
    moderator = "moderator"
    recipient = "recipient"


class RelayStatus(enum.StrEnum):
    pending = "pending"
    relayed = "relayed"
    dismissed = "dismissed"


class ModResponseScope(enum.StrEnum):
    sender_only = "sender_only"
    sender_circle = "sender_circle"
    all_circles = "all_circles"


class TransferStatus(enum.StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    denied = "denied"
    expired = "expired"
