import { PassThrough } from 'node:stream'

import { Box, renderSync } from '@hermes/ink'
import React from 'react'
import stripAnsi from 'strip-ansi'
import { expect, it, vi } from 'vitest'

import { applyAgentSnapshot } from '../app/agentRoster.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { AgentsOverlay } from '../components/agentsOverlay.js'
import type { GatewayClient } from '../gatewayClient.js'
import { DEFAULT_THEME } from '../theme.js'

const delay = (ms: number) => new Promise(r => setTimeout(r, ms))

const TOOL_LINES = Array.from({ length: 50 }, (_, i) => `tool-${String(i).padStart(2, '0')} · arguments for tool ${i}`)

it('keeps the open agent detail readable when the live roster drops the dispatch', async () => {
  patchUiState({ sid: 'owner' })
  applyAgentSnapshot('owner', {
    subagents: [
      { depth: 0, goal: 'Inspect ownership', status: 'running', subagent_id: 'child', tool_count: 50, tools: TOOL_LINES }
    ],
    delegations: []
  })

  const stdout = Object.assign(new PassThrough(), { columns: 80, rows: 24, isTTY: false })
  const stdin = Object.assign(new PassThrough(), { columns: 80, rows: 24, isTTY: true, setRawMode: () => {}, ref: () => {}, unref: () => {} })
  let output = ''
  stdout.on('data', chunk => {
    output += stripAnsi(chunk.toString())
  })

  const view = renderSync(
    <Box height={22} width={80}>
      <AgentsOverlay gw={{ request: vi.fn(async () => ({})) } as unknown as GatewayClient} onClose={() => {}} t={DEFAULT_THEME} />
    </Box>,
    {
      stdout: stdout as unknown as NodeJS.WriteStream,
      stdin: stdin as unknown as NodeJS.ReadStream,
      stderr: new PassThrough() as unknown as NodeJS.WriteStream,
      patchConsole: false
    }
  )

  try {
    await delay(120)
    stdin.write('d')
    await vi.waitFor(() => expect(output).toContain('Tool calls (50)'), { timeout: 3000 })
    expect(output).toContain('tool-00')

    // A background dispatch can unregister the moment its process ends. The
    // roster poll then returns an empty list while the user is still reading
    // the detail; the pane must keep showing what was open instead of
    // rendering an empty ScrollBox.
    output = ''
    applyAgentSnapshot('owner', { subagents: [], delegations: [] })
    await delay(700)

    expect(output).toContain('Tool calls (50)')
    expect(output).toContain('tool-00')
  } finally {
    view.unmount()
    view.cleanup()
    applyAgentSnapshot(null)
    resetUiState()
  }
})
