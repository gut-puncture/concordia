# Copyright 2026 DeepMind Technologies Limited.
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

"""MCP tool adapter for Concordia's core Tool interface."""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from concordia.document import tool as tool_module

_SENSITIVE_KEYWORDS = (
    'password',
    'credential',
    'secret',
    'token',
    'private',
)
_DESTRUCTIVE_KEYWORDS = (
    'delete',
    'drop',
    'remove',
    'update',
    'write',
)


def infer_risk_level(tool_name: str, description: str) -> str:
  """Infers a risk level from tool metadata."""
  normalized = f'{tool_name} {description}'.lower()
  if any(keyword in normalized for keyword in _DESTRUCTIVE_KEYWORDS):
    return 'destructive'
  if any(keyword in normalized for keyword in _SENSITIVE_KEYWORDS):
    return 'sensitive'
  return 'read'


class MCPTool(tool_module.Tool):
  """Wraps an MCP-style tool definition as a Concordia Tool."""

  def __init__(
      self,
      *,
      name: str,
      description: str,
      execute_fn: Callable[[dict[str, Any]], str],
      input_schema: Mapping[str, Any] | None = None,
      risk_level: str = 'read',
  ) -> None:
    self._name = name
    self._description = description
    self._execute_fn = execute_fn
    self._input_schema = input_schema
    self._risk_level = risk_level

  @property
  def name(self) -> str:
    return self._name

  @property
  def description(self) -> str:
    return self._description

  @property
  def input_schema(self) -> Mapping[str, Any] | None:
    return self._input_schema

  @property
  def risk_level(self) -> str:
    return self._risk_level

  def execute(self, **kwargs: Any) -> str:
    return self._execute_fn(kwargs)


def _extract_schema(definition: Mapping[str, Any]) -> Mapping[str, Any] | None:
  """Extracts an MCP input schema from a tool definition."""
  for key in ('input_schema', 'inputSchema'):
    schema = definition.get(key)
    if isinstance(schema, Mapping):
      return schema
  return None


def create_mcp_tools(
    *,
    tool_definitions: Sequence[Mapping[str, Any]],
    execute_fn: Callable[[str, dict[str, Any]], str],
) -> list[MCPTool]:
  """Creates MCPTool wrappers from MCP-style definitions."""
  tools: list[MCPTool] = []
  for definition in tool_definitions:
    if 'name' not in definition:
      raise ValueError('MCP tool definition missing required "name".')
    name = str(definition['name'])
    description = str(definition.get('description', ''))
    schema = _extract_schema(definition)
    risk_level = definition.get('risk_level')
    if not isinstance(risk_level, str):
      risk_level = infer_risk_level(name, description)

    def _execute(args: dict[str, Any], *, tool_name: str = name) -> str:
      return execute_fn(tool_name, args)

    tools.append(
        MCPTool(
            name=name,
            description=description,
            execute_fn=_execute,
            input_schema=schema,
            risk_level=risk_level,
        )
    )
  return tools
