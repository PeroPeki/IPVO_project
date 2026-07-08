import { useEffect, useState } from 'react';
import { api } from '../../api';

const STATUS_LABEL: Record<string, string> = {
  placed: 'Zaprimljena',
  accepted: 'Prihvaćena',
  preparing: 'U pripremi',
  delivered: 'Dostavljena',
  cancelled: 'Otkazana',
};

const STATUS_BADGE: Record<string, string> = {
  placed: 'warning',
  accepted: 'warning',
  preparing: 'warning',
  delivered: 'success',
  cancelled: 'error',
};

export default function Orders() {
  const [orders, setOrders] = useState<any[]>([]);
  const [error, setError] = useState('');

  function loadOrders() {
    api<{ orders: any[] }>('/api/orders/waiter')
      .then((d) => setOrders(d.orders))
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    loadOrders();
    const interval = setInterval(loadOrders, 5000);
    return () => clearInterval(interval);
  }, []);

  async function act(orderId: string, action: 'accept' | 'deliver' | 'collect-cash') {
    setError('');
    try {
      await api(`/api/orders/${orderId}/${action}`, { method: 'PUT' });
      loadOrders();
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <>
      <h1>Narudžbe ({orders.length})</h1>
      {error && <div className="error-msg">{error}</div>}

      <div className="grid cols-3">
        {orders.map((o) => {
          const actionLabel = o.order_status === 'placed' ? 'Prihvati'
            : ['accepted', 'preparing'].includes(o.order_status) ? 'Dostavljeno' : undefined;
          const cashPending = o.payment_method === 'cash' && o.payment_status === 'cash_pending'
            && ['accepted', 'preparing', 'delivered'].includes(o.order_status);
          return (
            <div className="card" key={o._id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>Stol {o.table_label}</strong>
                <span className={`badge ${STATUS_BADGE[o.order_status] ?? 'muted'}`}>
                  {STATUS_LABEL[o.order_status] ?? o.order_status}
                </span>
              </div>
              <div style={{ marginTop: 8 }}>
                {(o.items ?? []).map((i: any, idx: number) => (
                  <div key={idx} className="muted">{i.quantity}× {i.name}</div>
                ))}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
                <span className="muted" style={{ fontSize: 12 }}>
                  {o.payment_method === 'cash' ? 'Gotovina' : 'Kartica'}
                  {o.payment_status === 'paid' ? ' · plaćeno' : ''}
                  {o.payment_status === 'cash_pending' ? ' · čeka naplatu' : ''}
                  {o.coupon_applied ? ` · kupon −${o.coupon_applied} €` : ''}
                </span>
                <strong>{o.total} €</strong>
              </div>
              {actionLabel && (
                <button
                  style={{ marginTop: 12, width: '100%' }}
                  onClick={() => act(o._id, o.order_status === 'placed' ? 'accept' : 'deliver')}
                >
                  {actionLabel}
                </button>
              )}
              {cashPending && (
                <button
                  style={{ marginTop: 8, width: '100%' }}
                  onClick={() => act(o._id, 'collect-cash')}
                >
                  Naplaćeno gotovinom
                </button>
              )}
            </div>
          );
        })}
      </div>
      {orders.length === 0 && <p className="muted">Nema aktivnih narudžbi u tvojoj sekciji.</p>}
    </>
  );
}
