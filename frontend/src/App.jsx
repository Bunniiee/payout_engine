import { useState, useEffect } from 'react';
import { getMerchants, setMerchantId } from './api';
import BalanceCard from './components/BalanceCard';
import PayoutForm from './components/PayoutForm';
import LedgerTable from './components/LedgerTable';
import PayoutHistory from './components/PayoutHistory';

export default function App() {
  const [merchants, setMerchants] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    getMerchants()
      .then((res) => {
        const list = res.data;
        setMerchants(list);
        if (list.length > 0) {
          setSelectedId(list[0].id);
          setMerchantId(list[0].id);
        }
      })
      .catch(() => {});
  }, []);

  function handleMerchantChange(e) {
    const id = e.target.value;
    setSelectedId(id);
    setMerchantId(id);
    setRefreshKey((k) => k + 1);
  }

  function handlePayoutCreated() {
    setRefreshKey((k) => k + 1);
  }

  if (!selectedId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading merchants…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Playto Pay — Payout Dashboard</h1>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 font-medium">Merchant:</label>
          <select
            value={selectedId}
            onChange={handleMerchantChange}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {merchants.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        <BalanceCard key={`balance-${selectedId}-${refreshKey}`} />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <PayoutForm onPayoutCreated={handlePayoutCreated} />
          <LedgerTable key={`ledger-${selectedId}-${refreshKey}`} />
        </div>

        <PayoutHistory key={`history-${selectedId}-${refreshKey}`} />
      </main>
    </div>
  );
}
