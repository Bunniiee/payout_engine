import { useState, useEffect } from 'react';
import { getPayouts } from '../api';

const STATUS_STYLES = {
  pending:    'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed:  'bg-green-100 text-green-800',
  failed:     'bg-red-100 text-red-800',
};

function formatPaise(paise) {
  return `₹${(paise / 100).toFixed(2)}`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

export default function PayoutHistory() {
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);

  function fetchPayouts() {
    getPayouts()
      .then((res) => {
        setPayouts(res.data.results || res.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }

  useEffect(() => {
    fetchPayouts();
    const interval = setInterval(fetchPayouts, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-4">
        Payout History
      </h2>
      {loading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : payouts.length === 0 ? (
        <p className="text-sm text-gray-400">No payouts yet. Submit one above.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                <th className="pb-2 font-medium">ID</th>
                <th className="pb-2 font-medium">Amount</th>
                <th className="pb-2 font-medium">Bank Account</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium">Attempts</th>
                <th className="pb-2 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {payouts.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="py-2 pr-4 font-mono text-xs text-gray-500">
                    {p.id.slice(0, 8)}…
                  </td>
                  <td className="py-2 pr-4 font-medium text-gray-800">
                    {formatPaise(p.amount_paise)}
                  </td>
                  <td className="py-2 pr-4 text-gray-600 truncate max-w-[120px]">
                    {p.bank_account_id}
                  </td>
                  <td className="py-2 pr-4">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[p.status] || 'bg-gray-100 text-gray-600'}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-center text-gray-500">{p.attempts}</td>
                  <td className="py-2 text-xs text-gray-400">{formatDate(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
