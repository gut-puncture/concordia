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

"""Minimal example of policy-aware tool execution."""

from collections.abc import Collection, Mapping, Sequence
from typing import Any

from concordia.document import interactive_document_tools
from concordia.document import tool as tool_module
from concordia.document import tool_policy
from concordia.language_model import language_model


class _ScriptedLanguageModel(language_model.LanguageModel):
  """Simple deterministic model used for demonstration."""

  def __init__(self) -> None:
    self._responses = iter([
        '{"tool": "delete_file", "args": {"path": "/tmp/data.txt"}}',
        'I could not run the tool, but here is my answer.',
    ])

  def sample_text(
      self,
      prompt: str,
      *,
      max_tokens: int = language_model.DEFAULT_MAX_TOKENS,
      terminators: Collection[str] = language_model.DEFAULT_TERMINATORS,
      temperature: float = language_model.DEFAULT_TEMPERATURE,
      top_p: float = language_model.DEFAULT_TOP_P,
      top_k: int = language_model.DEFAULT_TOP_K,
      timeout: float = language_model.DEFAULT_TIMEOUT_SECONDS,
      seed: int | None = None,
  ) -> str:
    del prompt, max_tokens, terminators, temperature, top_p, top_k, timeout
    del seed
    return next(self._responses)

  def sample_choice(
      self,
      prompt: str,
      responses: Sequence[str],
      *,
      seed: int | None = None,
  ) -> tuple[int, str, Mapping[str, Any]]:
    del prompt, seed
    return 0, responses[0], {'debug': 'not used'}


class _DeleteFileTool(tool_module.Tool):
  """Example tool that would normally be considered destructive."""

  @property
  def name(self) -> str:
    return 'delete_file'

  @property
  def description(self) -> str:
    return 'Delete a file by path.'

  @property
  def input_schema(self) -> Mapping[str, Any] | None:
    return {'type': 'object', 'properties': {'path': {'type': 'string'}}}

  @property
  def risk_level(self) -> str:
    return 'destructive'

  def execute(self, **kwargs: Any) -> str:
    return 'Deleted ' + kwargs['path'] + '.'


class _BlockDestructivePolicy:
  """Blocks all destructive tools."""

  def evaluate(
      self,
      call: tool_policy.ToolCall,
      available_tools: Mapping[str, tool_module.Tool],
  ) -> tool_policy.PolicyDecision:
    tool = available_tools.get(call.tool_name)
    if tool and tool.risk_level == 'destructive':
      return tool_policy.PolicyDecision(
          action=tool_policy.PolicyAction.DENY,
          reason='Destructive tools are disabled.',
      )
    return tool_policy.PolicyDecision()


def main() -> None:
  model = _ScriptedLanguageModel()
  document = interactive_document_tools.InteractiveDocumentWithTools(
      model=model,
      tools=[_DeleteFileTool()],
      policy=_BlockDestructivePolicy(),
      enforcement_mode='enforce',
  )
  answer = document.open_question('Delete /tmp/data.txt and summarize result.')
  print(answer)
  print(document.text())


if __name__ == '__main__':
  main()
