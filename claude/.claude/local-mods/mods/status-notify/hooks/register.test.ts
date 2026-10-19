import { expect, test } from 'claude-code/testing'

const turn = (durationMs: number) => ({
  answer: 'done',
  durationMs,
  isAborted: false,
  turnId: 't1',
}) as never

function stub(on: Parameters<Parameters<typeof test>[1]>[1], argvs: string[][]) {
  on('session.model', () => ({ value: 'sonnet' }) as never)
  on('session.usage', () => ({
    value: {
      startedAt: 0,
      context: { window: 1000, percent: 12 },
      rateLimits: [
        { kind: 'five_hour', percentUsed: 31 },
        { kind: 'seven_day', percentUsed: 8 },
      ],
    },
  }) as never)
  on('turn.complete', () => ({ text: 'done' }) as never)
  on('process.run', (_$, e) => {
    argvs.push([...e.argv])

    return { value: { exitCode: 0, stdout: '# branch.head main\n# branch.ab +1 -0\n1 .M x\n', stderr: '' } } as never
  })
}

test('sends notify-send when a turn runs past the threshold', async ($, on) => {
  const argvs: string[][] = []
  stub(on, argvs)

  await $.turn.complete(turn(45_000))

  expect(argvs.some(a => a[0] === 'notify-send' && a.includes('Finished in 45s'))).toBe(true)
})

test('stays quiet for a short turn', async ($, on) => {
  const argvs: string[][] = []
  stub(on, argvs)

  await $.turn.complete(turn(5_000))

  expect(argvs.some(a => a[0] === 'notify-send')).toBe(false)
})
