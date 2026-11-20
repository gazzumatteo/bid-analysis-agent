# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for the HITL guard-rail — the demo's core governance pattern."""

from types import SimpleNamespace

import pytest
from google.genai import types

from app.agent import guard_workspace_tool

WORKSPACE = SimpleNamespace(name="setup_bid_workspace")


def _ctx(state: dict, invocation_id: str = "turn-2", user_text: str | None = None):
    content = (
        types.Content(role="user", parts=[types.Part(text=user_text)])
        if user_text is not None
        else None
    )
    return SimpleNamespace(
        state=state, invocation_id=invocation_id, user_content=content
    )


@pytest.mark.asyncio
async def test_guard_blocks_workspace_without_hitl() -> None:
    """setup_bid_workspace must be blocked if ask_bid_decision was never called."""
    result = await guard_workspace_tool(WORKSPACE, {}, _ctx({}, user_text="Go"))
    assert result is not None
    assert "error" in result


@pytest.mark.asyncio
async def test_guard_blocks_when_approval_was_only_requested() -> None:
    """Requesting approval in the same turn is not approval."""
    ctx = _ctx(
        {"hitl_requested_in": "turn-1"},
        invocation_id="turn-1",
        user_text="Analizza questo bando",
    )
    result = await guard_workspace_tool(WORKSPACE, {}, ctx)
    assert result is not None
    assert "error" in result


@pytest.mark.asyncio
async def test_guard_blocks_after_no_go() -> None:
    """A 'No-Go' answer must not open the workspace."""
    ctx = _ctx({"hitl_requested_in": "turn-1"}, user_text="No-Go. Non partecipate.")
    result = await guard_workspace_tool(WORKSPACE, {}, ctx)
    assert result is not None
    assert "error" in result


@pytest.mark.asyncio
async def test_guard_allows_workspace_after_go_once() -> None:
    """After a 'Go' in a later turn the guard passes, and only once."""
    state = {"hitl_requested_in": "turn-1"}
    assert (
        await guard_workspace_tool(WORKSPACE, {}, _ctx(state, user_text="Go, procedi"))
        is None
    )
    second = await guard_workspace_tool(WORKSPACE, {}, _ctx(state, user_text="Go"))
    assert second is not None
    assert "error" in second


@pytest.mark.asyncio
async def test_guard_ignores_other_tools() -> None:
    """Guard must only gate setup_bid_workspace, not unrelated tools."""
    tool = SimpleNamespace(name="read_tender")
    result = await guard_workspace_tool(tool, {}, _ctx({}))
    assert result is None
