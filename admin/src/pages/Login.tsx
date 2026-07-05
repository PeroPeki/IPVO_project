import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../api';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
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

  return (
    <div className="login-page">
      <form className="card login-box" onSubmit={submit}>
        <h1 style={{ color: 'var(--accent1)' }}>Admin prijava</h1>
        <label>Email (admin) / korisničko ime (superadmin)</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label>Lozinka</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <div className="error-msg">{error}</div>}
        <button style={{ marginTop: 16, width: '100%' }} disabled={loading}>
          {loading ? 'Prijava…' : 'Prijavi se'}
        </button>
      </form>
    </div>
  );
}
