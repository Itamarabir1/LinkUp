import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div style={{ padding: 24 }}>
      <header style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Admin</h2>
        <div style={{ color: '#666' }}>
          Signed in as <strong>{user?.full_name}</strong> ({user?.email ?? 'no-email'})
          {' · '}
          <button
            type="button"
            onClick={handleLogout}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#666',
              padding: 0,
            }}
          >
            Logout
          </button>
        </div>
        <nav style={{ marginTop: 10, display: 'flex', gap: 12 }}>
          <Link to="/admin">Home</Link>
          <Link to="/admin/health">Health</Link>
          <Link to="/admin/users">Users</Link>
          <Link to="/admin/outbox">Outbox</Link>
          <Link to="/admin/lookup">Lookup</Link>
        </nav>
      </header>
      <Outlet />
    </div>
  );
}
