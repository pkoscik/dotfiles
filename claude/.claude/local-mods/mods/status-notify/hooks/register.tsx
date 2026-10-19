import type { EngineInterface, Register } from 'claude-code'

const NAMES: Record<string, string> = { five_hour: '5h', seven_day: '7d' }

async function send($: EngineInterface, body: string, isUrgent = false) {
  try {
    await $.process.run([
      'notify-send',
      '--app-name=Claude Code',
      `--urgency=${isUrgent ? 'critical' : 'normal'}`,
      'Claude Code',
      body,
    ])
  } catch {
    $.ui.toast(body)
  }
}

function resetText(resetsAt: string | undefined) {
  const at = resetsAt === undefined ? null : new Date(resetsAt)

  if (at === null || Number.isNaN(at.getTime())) {
    return ''
  }

  const hours = String(at.getHours()).padStart(2, '0')
  const minutes = String(at.getMinutes()).padStart(2, '0')
  const day = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][at.getDay()]

  return ` — resets ${Date.now() + 18 * 3_600_000 < at.getTime() ? `${day} ` : ''}${hours}:${minutes}`
}

export const register: Register = (on, options) => {
  const notifyAfterMs = Number(options.notifyAfterSeconds ?? 30) * 1000
  const warnAt = Number(options.limitWarnPercent ?? 80)
  const criticalAt = Number(options.limitCriticalPercent ?? 95)
  const nudgeAt = Number(options.contextNudgePercent ?? 70)
  let isNudged = false

  on('session.measure', async ($, e, next) => {
    for (const limit of e.rateLimits) {
      const name = NAMES[limit.kind]
      const level = limit.percentUsed >= criticalAt ? criticalAt : limit.percentUsed >= warnAt ? warnAt : 0

      if (name === undefined || level === 0) {
        continue
      }

      const prefix = `alert:${limit.kind}:`
      const key = `${prefix}${limit.resetsAt ?? 'unknown'}:${level}`

      // One alert per window, level and reset; other sessions share the store.
      if ((await $.store.get(key)) !== undefined) {
        continue
      }

      for (const stale of await $.store.keys()) {
        if (stale.startsWith(prefix) && !stale.startsWith(`${prefix}${limit.resetsAt ?? 'unknown'}:`)) {
          await $.store.delete(stale)
        }
      }

      await $.store.set(key, true)
      await send(
        $,
        `${name} limit at ${Math.round(limit.percentUsed)}%${resetText(limit.resetsAt)}`,
        level === criticalAt,
      )
    }

    const percent = e.context.percent

    if (percent !== undefined) {
      if (percent >= nudgeAt && !isNudged) {
        isNudged = true
        $.ui.toast(`Context at ${Math.round(percent)}% — consider /compact`, { timeoutMs: 8000 })
      } else if (percent < nudgeAt - 20) {
        isNudged = false
      }
    }


    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (e.agentId === undefined && !e.isAborted && e.durationMs >= notifyAfterMs) {
      await send($, `Finished in ${Math.round(e.durationMs / 1000)}s`)
    }

    return next(e)
  })
}
