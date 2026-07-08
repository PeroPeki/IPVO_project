import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../api';

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'admin' | 'staff'>('admin');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const url = mode === 'admin' ? '/api/auth/admin/login' : '/api/auth/staff/login';
      const body = mode === 'admin' ? { email, password } : { email, pin };
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Prijava nije uspjela');
      auth.login(data.access_token, data.role);
      navigate('/');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function switchMode(next: 'admin' | 'staff') {
    setMode(next);
    setError('');
  }

  return (
    <div className="login-page">
      <form className="card login-box" onSubmit={submit}>
        <h1 style={{ color: 'var(--accent1)' }}>Prijava</h1>

        <div className="form-row" style={{ marginBottom: 16 }}>
          <button
            type="button"
            className={mode === 'admin' ? '' : 'secondary'}
            onClick={() => switchMode('admin')}
          >
            Admin
          </button>
          <button
            type="button"
            className={mode === 'staff' ? '' : 'secondary'}
            onClick={() => switchMode('staff')}
          >
            Osoblje
          </button>
        </div>

        {mode === 'admin' ? (
          <>
            <label>Email (admin) / korisničko ime (superadmin)</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} required />
            <label>Lozinka</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </>
        ) : (
          <>
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} required />
            <label>PIN (4 znamenke)</label>
            <input
              value={pin} maxLength={4} pattern="\d{4}" inputMode="numeric"
              onChange={(e) => setPin(e.target.value)} required
            />
          </>
        )}

        {error && <div className="error-msg">{error}</div>}
        <button style={{ marginTop: 16, width: '100%' }} disabled={loading}>
          {loading ? 'Prijava…' : 'Prijavi se'}
        </button>
      </form>
    </div>
  );
}
