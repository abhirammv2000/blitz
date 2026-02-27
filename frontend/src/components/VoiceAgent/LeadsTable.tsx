import { useEffect, useState } from 'react'
import { API_BASE } from '../../config'

interface Lead {
  id: number
  run_id: string
  company_name: string | null
  caller_name: string | null
  email: string | null
  phone: string | null
  callback_time: string | null
  conversation_id: string | null
  interested: number | null
  extracted_at: string | null
}

interface LeadsTableProps {
  runId: string
}

export default function LeadsTable({ runId }: LeadsTableProps) {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/voice/leads/${runId}`)
      .then((res) => res.json())
      .then((data) => {
        setLeads(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [runId])

  if (loading) {
    return (
      <div className="text-sm text-ink-faint animate-pulse py-3">
        Loading leads...
      </div>
    )
  }

  if (leads.length === 0) return null

  return (
    <div className="rounded-xl border border-ink/10 overflow-hidden">
      <div className="px-4 py-3 bg-cream-dark border-b border-ink/10">
        <p className="text-xs text-ink-faint uppercase tracking-widest font-medium">
          Captured Leads
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-ink/10 bg-cream-dark/50">
              <th className="text-left px-4 py-2 text-xs text-ink-faint font-medium">Name</th>
              <th className="text-left px-4 py-2 text-xs text-ink-faint font-medium">Email</th>
              <th className="text-left px-4 py-2 text-xs text-ink-faint font-medium">Phone</th>
              <th className="text-left px-4 py-2 text-xs text-ink-faint font-medium">Callback</th>
              <th className="text-left px-4 py-2 text-xs text-ink-faint font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead) => (
              <tr key={lead.id} className="border-b border-ink/5 last:border-b-0">
                <td className="px-4 py-2.5 text-ink">{lead.caller_name || '—'}</td>
                <td className="px-4 py-2.5 text-ink">{lead.email || '—'}</td>
                <td className="px-4 py-2.5 text-ink">{lead.phone || '—'}</td>
                <td className="px-4 py-2.5 text-ink">{lead.callback_time || '—'}</td>
                <td className="px-4 py-2.5">
                  {lead.interested === 1 ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-teal-600/10 text-teal-700">
                      Interested
                    </span>
                  ) : lead.interested === 0 ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-ink/5 text-ink-faint">
                      Not interested
                    </span>
                  ) : (
                    <span className="text-ink-faint">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
