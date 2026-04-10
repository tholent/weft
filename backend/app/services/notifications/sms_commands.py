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

"""SMS command parser.

Recognises keyword commands sent by members via SMS reply:

    STOP   — opt out of all SMS notifications (mute all triggers)
    MUTE   — same as STOP, Weft-specific alias
    RESUME — re-enable immediate delivery on all triggers
    LIST   — reply with a list of active topic short codes for this phone number

Commands are case-insensitive and must appear as the entire message body
(possibly with leading/trailing whitespace). Anything else is treated as
a non-command reply.
"""

from enum import StrEnum


class SmsCommand(StrEnum):
    stop = "stop"
    mute = "mute"
    resume = "resume"
    list = "list"


# Normalised keyword → command mapping
_KEYWORDS: dict[str, SmsCommand] = {
    "stop": SmsCommand.stop,
    "mute": SmsCommand.mute,
    "resume": SmsCommand.resume,
    "list": SmsCommand.list,
}


def parse_sms_command(body: str) -> SmsCommand | None:
    """Return the ``SmsCommand`` if *body* is a recognised command, else ``None``.

    Matching is case-insensitive and ignores surrounding whitespace.  Only
    exact single-keyword messages are treated as commands; anything longer
    is a regular reply.
    """
    normalised = body.strip().lower()
    return _KEYWORDS.get(normalised)


def is_sms_command(body: str) -> bool:
    """Return ``True`` if *body* is a recognised SMS command."""
    return parse_sms_command(body) is not None
