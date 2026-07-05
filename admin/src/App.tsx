import { Navigate, Route, Routes } from 'react-router-dom';
import { auth } from './api';
import Layout from './components/Layout';
import ClubForm from './pages/Clubs/ClubForm';
import ClubList from './pages/Clubs/ClubList';
import Dashboard from './pages/Dashboard';
import EventForm from './pages/Events/EventForm';
import EventList from './pages/Events/EventList';
import FloorMapEditor from './pages/FloorMapEditor/Canvas';
import LiveDashboard from './pages/LiveDashboard';
import Login from './pages/Login';
import MenuEditor from './pages/Menu/MenuEditor';
import Reports from './pages/Reports';
import Reservations from './pages/Reservations';
import StaffList from './pages/Staff/StaffList';

function Protected({ children }: { children: JSX.Element }) {
  if (!auth.token) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/clubs" element={<Protected><ClubList /></Protected>} />
      <Route path="/clubs/new" element={<Protected><ClubForm /></Protected>} />
      <Route path="/clubs/:id/edit" element={<Protected><ClubForm /></Protected>} />
      <Route path="/events" element={<Protected><EventList /></Protected>} />
      <Route path="/events/new" element={<Protected><EventForm /></Protected>} />
      <Route path="/events/:id/edit" element={<Protected><EventForm /></Protected>} />
      <Route path="/events/:id/live" element={<Protected><LiveDashboard /></Protected>} />
      <Route path="/events/:id/reservations" element={<Protected><Reservations /></Protected>} />
      <Route path="/floor-map" element={<Protected><FloorMapEditor /></Protected>} />
      <Route path="/staff" element={<Protected><StaffList /></Protected>} />
      <Route path="/menu" element={<Protected><MenuEditor /></Protected>} />
      <Route path="/reports" element={<Protected><Reports /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
