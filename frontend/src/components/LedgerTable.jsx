import { useState, useEffect } from 'react';
import { getLedger } from '../api';

function formatPaise(paise) {
  const sign = paise >= 0 ? '+' : '';
  return `${sign}₹${(Math.abs(paise) / 100).toFixed(2)}`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

const ENTRY_LABELS = {
  CREDIT: 'Credit',
  HOLD: 'Hold',
  HOLD_RELEASE: 'Released',
};

export default function LedgerTable() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLedger()
      .then((res) => setEntries(res.data.results || res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-4">
        Recent Ledger
      </h2>
      {loading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-gray-400">No entries yet.</p>
      ) : (
        <div className="overflow-auto max-h-72">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                <th className="pb-2 font-medium">Type</th>
                <th className="pb-2 font-medium text-right">Amount</th>
                <th className="pb-2 font-medium text-right">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {entries.map((e) => (
                <tr key={e.id}>
                  <td className="py-1.5 pr-2">
                    <span className="text-xs font-medium text-gray-600">
                      {ENTRY_LABELS[e.entry_type] || e.entry_type}
                    </span>
                  </td>
                  <td className={`py-1.5 text-right font-mono font-medium ${
                    e.amount_paise >= 0 ? 'text-green-600' : 'text-red-500'
                  }`}>
                    {formatPaise(e.amount_paise)}
                  </td>
                  <td className="py-1.5 text-right text-xs text-gray-400">
                    {formatDate(e.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
