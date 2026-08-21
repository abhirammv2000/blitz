import { useEffect, useState } from 'react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { API_BASE } from '../config'

interface Summary {
  calls: number
  runs: number
  total_cost_usd: number
  total_tokens: number
  avg_latency_ms: number
  successes: number
  failures: number
  avg_cost_per_run_usd: number
  avg_tokens_per_run: number
  success_rate: number
  by_provider: { provider: string; calls: number; cost_usd: number; tokens: number }[]
  by_model_group: { model_group: string; calls: number; cost_usd: number }[]
}

interface AgentCost {
  agent: string
  calls: number
  cost_usd: number
  tokens: number
  avg_latency_ms: number
  max_latency_ms: number
}

interface RunRow {
  run_id: string
  started_at: string
  calls: number
  cost_usd: number
  tokens: number
  total_latency_ms: number
  failures: number
}

const usd = (n: number) => `$${n.toFixed(4)}`
const int = (n: number) => n.toLocaleString()
const secs = (ms: number) => `${(ms / 1000).toFixed(1)}s`

// Deliberately ordered: the agent that costs most is the one worth reading first.
const BAR_COLORS = ['#B4552D', '#C97B4E', '#7C8A6B', '#9AA88A', '#C3B59A', '#D6CDBB']

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-ink/10 bg-white p-5">
      <p className="text-xs uppercase tracking-widest text-ink-faint font-medium">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
      {sub && <p className="mt-1 text-xs text-ink-faint">{sub}</p>}
    </div>
  )
}

export default function Telemetry() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [agents, setAgents] = useState<AgentCost[]>([])
  const [runs, setRuns] = useState<RunRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [s, a, r] = await Promise.all([
          fetch(`${API_BASE}/telemetry/summary`).then((x) => x.json()),
          fetch(`${API_BASE}/telemetry/agents`).then((x) => x.json()),
          fetch(`${API_BASE}/telemetry/runs`).then((x) => x.json()),
        ])
        if (cancelled) return
        setSummary(s)
        setAgents(a)
        setRuns(r)
        setError(null)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load telemetry')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    // Cheap polling: this is an internal dashboard, not a hot path.
    const timer = setInterval(load, 10000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  if (loading) {
    return <div className="p-10 text-ink-faint">Loading telemetry…</div>
  }
  if (error) {
    return <div className="p-10 text-[#B4552D]">Could not reach the telemetry API: {error}</div>
  }
  if (!summary || summary.calls === 0) {
    return (
      <div className="p-10">
        <h1 className="text-2xl font-semibold text-ink">AI Telemetry</h1>
        <p className="mt-3 text-ink-faint">
          No LLM calls recorded yet. Run a pipeline and this fills in.
        </p>
      </div>
    )
  }

  const chartData = agents.map((a) => ({
    name: a.agent.replace(/^agent_\d_/, '').replace(/_/g, ' '),
    cost: Number(a.cost_usd.toFixed(4)),
    tokens: a.tokens,
  }))
  const topAgent = agents[0]
  const topShare = topAgent ? (topAgent.cost_usd / summary.total_cost_usd) * 100 : 0

  return (
    <div className="min-h-screen bg-cream p-8 md:p-10">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold text-ink">AI Telemetry</h1>
        <p className="mt-2 text-sm text-ink-faint">
          Usage, cost, and reliability across every LLM call in the pipeline.
        </p>
      </header>

      <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Tile label="Cost / run" value={usd(summary.avg_cost_per_run_usd)} sub={`${summary.runs} run(s)`} />
        <Tile label="Total spend" value={usd(summary.total_cost_usd)} sub={`${int(summary.calls)} calls`} />
        <Tile label="Tokens / run" value={int(Math.round(summary.avg_tokens_per_run))} sub={`${int(summary.total_tokens)} total`} />
        <Tile
          label="Success rate"
          value={`${(summary.success_rate * 100).toFixed(0)}%`}
          sub={summary.failures > 0 ? `${summary.failures} failed call(s)` : 'no failures'}
        />
      </section>

      {topAgent && (
        <p className="mt-6 rounded-xl border border-ink/10 bg-white px-5 py-4 text-sm text-ink">
          <span className="font-semibold">{topAgent.agent}</span> accounts for{' '}
          <span className="font-semibold">{topShare.toFixed(0)}%</span> of spend across{' '}
          {topAgent.calls} calls — the first place to look when optimising cost.
        </p>
      )}

      <section className="mt-8 rounded-2xl border border-ink/10 bg-white p-6">
        <h2 className="text-sm font-medium uppercase tracking-widest text-ink-faint">Cost by agent</h2>
        <div className="mt-5 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#6B6255' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 12, fill: '#6B6255' }} tickLine={false} axisLine={false} />
              <Tooltip
                formatter={(v, n) =>
                  typeof v !== 'number' ? '—' : n === 'cost' ? usd(v) : int(v)
                }
                contentStyle={{ borderRadius: 12, border: '1px solid rgba(0,0,0,.1)' }}
              />
              <Bar dataKey="cost" radius={[6, 6, 0, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <section className="rounded-2xl border border-ink/10 bg-white p-6">
          <h2 className="text-sm font-medium uppercase tracking-widest text-ink-faint">By provider</h2>
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="text-left text-ink-faint">
                <th className="pb-2 font-medium">Provider</th>
                <th className="pb-2 text-right font-medium">Calls</th>
                <th className="pb-2 text-right font-medium">Cost</th>
              </tr>
            </thead>
            <tbody>
              {summary.by_provider.map((p) => (
                <tr key={p.provider} className="border-t border-ink/5">
                  <td className="py-2 text-ink">{p.provider}</td>
                  <td className="py-2 text-right text-ink">{int(p.calls)}</td>
                  <td className="py-2 text-right text-ink">{usd(p.cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="rounded-2xl border border-ink/10 bg-white p-6">
          <h2 className="text-sm font-medium uppercase tracking-widest text-ink-faint">By model tier</h2>
          <table className="mt-4 w-full text-sm">
            <thead>
              <tr className="text-left text-ink-faint">
                <th className="pb-2 font-medium">Tier</th>
                <th className="pb-2 text-right font-medium">Calls</th>
                <th className="pb-2 text-right font-medium">Cost</th>
              </tr>
            </thead>
            <tbody>
              {summary.by_model_group.map((g) => (
                <tr key={g.model_group} className="border-t border-ink/5">
                  <td className="py-2 text-ink">{g.model_group}</td>
                  <td className="py-2 text-right text-ink">{int(g.calls)}</td>
                  <td className="py-2 text-right text-ink">{usd(g.cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <section className="mt-6 rounded-2xl border border-ink/10 bg-white p-6">
        <h2 className="text-sm font-medium uppercase tracking-widest text-ink-faint">Recent runs</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ink-faint">
                <th className="pb-2 font-medium">Run</th>
                <th className="pb-2 text-right font-medium">Calls</th>
                <th className="pb-2 text-right font-medium">Tokens</th>
                <th className="pb-2 text-right font-medium">LLM time</th>
                <th className="pb-2 text-right font-medium">Cost</th>
                <th className="pb-2 text-right font-medium">Failed</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id} className="border-t border-ink/5">
                  <td className="py-2 font-mono text-xs text-ink">{r.run_id.slice(0, 8)}</td>
                  <td className="py-2 text-right text-ink">{int(r.calls)}</td>
                  <td className="py-2 text-right text-ink">{int(r.tokens)}</td>
                  <td className="py-2 text-right text-ink">{secs(r.total_latency_ms)}</td>
                  <td className="py-2 text-right text-ink">{usd(r.cost_usd)}</td>
                  <td className={`py-2 text-right ${r.failures > 0 ? 'text-[#B4552D]' : 'text-ink-faint'}`}>
                    {r.failures}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
