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

from app.agent import guard_workspace_tool


@pytest.mark.asyncio
async def test_guard_blocks_workspace_without_hitl() -> None:
    """setup_bid_workspace must be blocked if ask_bid_decision was never called."""
    tool = SimpleNamespace(name="setup_bid_workspace")
    tool_context = SimpleNamespace(state={})
    result = await guard_workspace_tool(tool, {}, tool_context)
    assert result is not None
    assert "error" in result


@pytest.mark.asyncio
async def test_guard_allows_workspace_after_hitl() -> None:
    """Once hitl_requested is set, the guard must pass-through (return None)."""
    tool = SimpleNamespace(name="setup_bid_workspace")
    tool_context = SimpleNamespace(state={"hitl_requested": True})
    result = await guard_workspace_tool(tool, {}, tool_context)
    assert result is None


@pytest.mark.asyncio
async def test_guard_ignores_other_tools() -> None:
    """Guard must only gate setup_bid_workspace, not unrelated tools."""
    tool = SimpleNamespace(name="read_tender")
    tool_context = SimpleNamespace(state={})
    result = await guard_workspace_tool(tool, {}, tool_context)
    assert result is None
