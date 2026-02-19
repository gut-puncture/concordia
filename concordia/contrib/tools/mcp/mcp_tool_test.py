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

"""Tests for MCP tool wrappers."""

from absl.testing import absltest
from concordia.contrib.tools.mcp import mcp_tool


class MCPToolTest(absltest.TestCase):

  def test_infer_risk_level(self):
    self.assertEqual(
        mcp_tool.infer_risk_level('read_file', 'Read a local file'), 'read'
    )
    self.assertEqual(
        mcp_tool.infer_risk_level('get_secret', 'Read secret token'),
        'sensitive',
    )
    self.assertEqual(
        mcp_tool.infer_risk_level('delete_file', 'Delete a local file'),
        'destructive',
    )

  def test_mcp_tool_exposes_metadata(self):
    calls: list[dict[str, object]] = []

    def execute(args: dict[str, object]) -> str:
      calls.append(args)
      return 'ok'

    tool = mcp_tool.MCPTool(
        name='read_file',
        description='Reads files.',
        execute_fn=execute,
        input_schema={'type': 'object'},
        risk_level='sensitive',
    )

    result = tool.execute(path='/tmp/test.txt')

    self.assertEqual(result, 'ok')
    self.assertEqual(calls, [{'path': '/tmp/test.txt'}])
    self.assertEqual(tool.input_schema, {'type': 'object'})
    self.assertEqual(tool.risk_level, 'sensitive')

  def test_create_mcp_tools_uses_schema_and_forwarder(self):
    calls: list[tuple[str, dict[str, object]]] = []

    def execute(tool_name: str, args: dict[str, object]) -> str:
      calls.append((tool_name, args))
      return f'result:{tool_name}'

    tools = mcp_tool.create_mcp_tools(
        tool_definitions=[
            {
                'name': 'list_directory',
                'description': 'List files in a directory',
                'inputSchema': {'type': 'object'},
            }
        ],
        execute_fn=execute,
    )

    self.assertLen(tools, 1)
    self.assertEqual(tools[0].input_schema, {'type': 'object'})
    self.assertEqual(tools[0].risk_level, 'read')
    self.assertEqual(tools[0].execute(path='/tmp'), 'result:list_directory')
    self.assertEqual(calls, [('list_directory', {'path': '/tmp'})])


if __name__ == '__main__':
  absltest.main()
