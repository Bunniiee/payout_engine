import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { createPayout } from '../api';

export default function PayoutForm({ onPayoutCreated }) {
  const [amountRupees, setAmountRupees] = useState('');
  const [bankAccountId, setBankAccountId] = useState('');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    const amount = parseFloat(amountRupees);
    if (!amount || amount <= 0) {
      setStatus({ type: 'error', message: 'Enter a valid amount in rupees.' });
      return;
    }
    if (!bankAccountId.trim()) {
      setStatus({ type: 'error', message: 'Bank account ID is required.' });
      return;
    }

    const idempotencyKey = uuidv4();
    const amountPaise = Math.round(amount * 100);

    setLoading(true);
    setStatus(null);

    try {
      const res = await createPayout(
        { amount_paise: amountPaise, bank_account_id: bankAccountId.trim() },
        idempotencyKey
      );
      const payout = res.data;
      const isNew = res.status === 201;
      setStatus({
        type: 'success',
        message: `${isNew ? 'Payout created' : 'Duplicate — existing payout returned'}: ${payout.id.slice(0, 8)}…  (${payout.status})`,
      });
      setAmountRupees('');
      if (onPayoutCreated) onPayoutCreated();
    } catch (err) {
      const msg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        JSON.stringify(err.response?.data) ||
        'Request failed';
      setStatus({ type: 'error', message: msg });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-4">
        Request Payout
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Amount (₹)
          </label>
          <input
            type="number"
            min="1"
            step="0.01"
            value={amountRupees}
            onChange={(e) => setAmountRupees(e.target.value)}
            placeholder="e.g. 500"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bank Account ID
          </label>
          <input
            type="text"
            value={bankAccountId}
            onChange={(e) => setBankAccountId(e.target.value)}
            placeholder="e.g. HDFC_ACC_001"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {status && (
          <div
            className={`text-sm rounded px-3 py-2 ${
              status.type === 'success'
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}
          >
            {status.message}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {loading ? 'Submitting…' : 'Request Payout'}
        </button>
      </form>
    </div>
  );
}
