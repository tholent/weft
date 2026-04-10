# Copyright 2026 Chris Wells <chris@tholent.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import enum


class TopicStatus(enum.StrEnum):
    active = "active"
    closed = "closed"
    archived = "archived"


class MemberRole(enum.StrEnum):
    owner = "owner"
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


class NotificationChannel(enum.StrEnum):
    email = "email"
    sms = "sms"


class DeliveryMode(enum.StrEnum):
    immediate = "immediate"
    digest = "digest"
    muted = "muted"


class NotificationTrigger(enum.StrEnum):
    new_update = "new_update"
    new_reply = "new_reply"
    mod_response = "mod_response"
    invite = "invite"
    relay = "relay"
    digest = "digest"


class NotificationStatus(enum.StrEnum):
    pending = "pending"
    pending_digest = "pending_digest"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"
