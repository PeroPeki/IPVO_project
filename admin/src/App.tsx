import { Navigate, Route, Routes } from 'react-router-dom';
import { auth } from './api';
import Layout from './components/Layout';
import Accounts from './pages/Accounts/Accounts';
import CheckIn from './pages/CheckIn/CheckIn';
import ClubForm from './pages/Clubs/ClubForm';
import ClubList from './pages/Clubs/ClubList';
import Dashboard from './pages/Dashboard';
import EventForm from './pages/Events/EventForm';
import EventList from './pages/Events/EventList';
import FloorMapEditor from './pages/FloorMapEditor/Canvas';
import LiveDashboard from './pages/LiveDashboard';
import Login from './pages/Login';
import MenuEditor from './pages/Menu/MenuEditor';
import Orders from './pages/Waiter/Orders';
import Reports from './pages/Reports';
import Reservations from './pages/Reservations';
import StaffList from './pages/Staff/StaffList';

function roleHome(role: string | null): string {
  if (role === 'hostess') return '/checkin';
  if (role === 'waiter') return '/orders';
  return '/';
}

function Protected({ children, allow }: { children: JSX.Element; allow: string[] }) {
  if (!auth.token) return <Navigate to="/login" replace />;
  if (!allow.includes(auth.role || '')) return <Navigate to={roleHome(auth.role)} replace />;
  return <Layout>{children}</Layout>;
}

const ADMIN_ROLES = ['admin', 'superadmin'];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected allow={ADMIN_ROLES}><Dashboard /></Protected>} />
      <Route path="/clubs" element={<Protected allow={ADMIN_ROLES}><ClubList /></Protected>} />
      <Route path="/clubs/new" element={<Protected allow={ADMIN_ROLES}><ClubForm /></Protected>} />
      <Route path="/clubs/:id/edit" element={<Protected allow={ADMIN_ROLES}><ClubForm /></Protected>} />
      <Route path="/events" element={<Protected allow={ADMIN_ROLES}><EventList /></Protected>} />
      <Route path="/events/new" element={<Protected allow={ADMIN_ROLES}><EventForm /></Protected>} />
      <Route path="/events/:id/edit" element={<Protected allow={ADMIN_ROLES}><EventForm /></Protected>} />
      <Route path="/events/:id/live" element={<Protected allow={ADMIN_ROLES}><LiveDashboard /></Protected>} />
      <Route path="/events/:id/reservations" element={<Protected allow={ADMIN_ROLES}><Reservations /></Protected>} />
      <Route path="/floor-map" element={<Protected allow={ADMIN_ROLES}><FloorMapEditor /></Protected>} />
      <Route path="/staff" element={<Protected allow={ADMIN_ROLES}><StaffList /></Protected>} />
      <Route path="/menu" element={<Protected allow={ADMIN_ROLES}><MenuEditor /></Protected>} />
      <Route path="/reports" element={<Protected allow={ADMIN_ROLES}><Reports /></Protected>} />
      <Route path="/accounts" element={<Protected allow={['superadmin']}><Accounts /></Protected>} />
      <Route path="/checkin" element={<Protected allow={['hostess']}><CheckIn /></Protected>} />
      <Route path="/orders" element={<Protected allow={['waiter']}><Orders /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
