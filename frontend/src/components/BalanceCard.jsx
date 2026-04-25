import { useState, useEffect } from 'react';
import { getMerchant } from '../api';

function formatPaise(paise) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(paise / 100);
}

export default function BalanceCard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  function fetchBalance() {
    getMerchant()
      .then((res) => { setData(res.data); setError(null); })
      .catch(() => setError('Failed to load balance'));
  }

  useEffect(() => {
    fetchBalance();
    const interval = setInterval(fetchBalance, 5000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm">{error}</div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-32 mb-3" />
        <div className="h-8 bg-gray-200 rounded w-48" />
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-4">
        {data.name} — Balance
      </h2>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <p className="text-xs text-gray-400 mb-1">Available</p>
          <p className="text-3xl font-bold text-green-600">
            {formatPaise(data.available_balance_paise)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-1">Held (in-flight)</p>
          <p className="text-3xl font-bold text-yellow-500">
            {formatPaise(data.held_balance_paise)}
          </p>
        </div>
      </div>
    </div>
  );
}
