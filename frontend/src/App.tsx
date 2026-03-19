import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { GroupProvider } from './context/GroupContext';
import { ChatProvider } from './context/ChatContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import VerifyEmail from './pages/VerifyEmail';
import MyRides from './pages/MyRides';
import CreateRide from './pages/CreateRide';
import SearchRides from './pages/SearchRides';
import MyRequests from './pages/MyRequests';
import MyBookings from './pages/MyBookings';
import Notifications from './pages/Notifications';
import Messages from './pages/Messages';
import MessageThread from './pages/MessageThread';
import Profile from './pages/Profile';
import CreateGroup from './pages/CreateGroup';
import Groups from './pages/Groups';
import GroupManage from './pages/GroupManage';
import JoinGroup from './pages/JoinGroup';
import FCMCheck from './pages/FCMCheck';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return <div className="page-loading" style={{ padding: '3rem', textAlign: 'center' }}>טוען...</div>;
  }
  if (!isAuthenticated) {
    const from = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?from=${from}`} replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/my-rides" replace />} />
        <Route path="my-rides" element={<MyRides />} />
        <Route path="create-ride" element={<CreateRide />} />
        <Route path="search" element={<SearchRides />} />
        <Route path="my-requests" element={<MyRequests />} />
        <Route path="my-bookings" element={<MyBookings />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="messages" element={<Messages />} />
        <Route path="messages/:conversationId" element={<MessageThread />} />
        <Route path="profile" element={<Profile />} />
        <Route path="groups" element={<Groups />} />
        <Route path="groups/new" element={<CreateGroup />} />
        <Route path="groups/:groupId" element={<GroupManage />} />
        <Route path="join/:inviteCode" element={<JoinGroup />} />
        <Route path="rides/:rideId" element={<Navigate to="/my-bookings?tab=driver" replace />} />
        <Route path="fcm-check" element={<FCMCheck />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <GroupProvider>
          {/* ChatProvider must be inside Router so useLocation() works */}
          <ChatProvider>
            <AppRoutes />
          </ChatProvider>
        </GroupProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
