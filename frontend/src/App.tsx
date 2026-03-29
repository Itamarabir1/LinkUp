import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import RouteErrorBoundary from './components/RouteErrorBoundary';
import ThemeToggle from './components/ThemeToggle/ThemeToggle';
import { AuthProvider, useAuth } from './context/AuthContext';
import { GroupProvider } from './context/GroupContext';
import { ChatProvider } from './context/ChatContext';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import PageLoading from './components/PageLoading';
import styles from './App.module.css';
import { AdminRoute } from './features/admin';

const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const VerifyEmail = lazy(() => import('./pages/VerifyEmail'));
const MyRides = lazy(() => import('./pages/MyRides'));
const CreateRide = lazy(() => import('./pages/CreateRide'));
const SearchRides = lazy(() => import('./pages/SearchRides'));
const MyRequests = lazy(() => import('./pages/MyRequests'));
const MyBookings = lazy(() => import('./pages/MyBookings'));
const Notifications = lazy(() => import('./pages/Notifications'));
const Messages = lazy(() => import('./pages/Messages'));
const MessageThread = lazy(() => import('./pages/MessageThread'));
const Profile = lazy(() => import('./pages/Profile'));
const CreateGroup = lazy(() => import('./pages/CreateGroup'));
const Groups = lazy(() => import('./pages/Groups'));
const GroupManage = lazy(() => import('./pages/GroupManage'));
const JoinGroup = lazy(() => import('./pages/JoinGroup'));
const FCMCheck = lazy(() => import('./pages/FCMCheck'));
const PostLoginHub = lazy(() => import('./pages/PostLoginHub'));
const Sablat = lazy(() => import('./pages/Sablat'));

const AdminLayout = lazy(() => import('./features/admin/pages/AdminLayout'));
const AdminHome = lazy(() => import('./features/admin/pages/AdminHome'));
const AdminHealth = lazy(() => import('./features/admin/pages/AdminHealth'));
const AdminUsers = lazy(() => import('./features/admin/pages/AdminUsers'));
const AdminOutbox = lazy(() => import('./features/admin/pages/AdminOutbox'));
const AdminLookup = lazy(() => import('./features/admin/pages/AdminLookup'));
const AdminRides = lazy(() => import('./features/admin/pages/AdminRides'));
const AdminGroups = lazy(() => import('./features/admin/pages/AdminGroups'));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return <div className={styles.pageLoading}>טוען...</div>;
  }
  if (!isAuthenticated) {
    const from = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?from=${from}`} replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  const location = useLocation();
  return (
    <RouteErrorBoundary resetKey={location.pathname}>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify-email" element={<VerifyEmail />} />

          <Route
            path="/admin"
            element={
              <AdminRoute>
                <AdminLayout />
              </AdminRoute>
            }
          >
            <Route index element={<AdminHome />} />
            <Route path="health" element={<AdminHealth />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="rides" element={<AdminRides />} />
            <Route path="groups" element={<AdminGroups />} />
            <Route path="outbox" element={<AdminOutbox />} />
            <Route path="lookup" element={<AdminLookup />} />
          </Route>

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/my-rides" replace />} />
            <Route path="choose-destination" element={<PostLoginHub />} />
            <Route path="sablat" element={<Sablat />} />
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
            <Route path="groups/:groupId/rides/search" element={<SearchRides />} />
            <Route path="groups/:groupId/rides/create" element={<CreateRide />} />
            <Route path="groups/:groupId" element={<GroupManage />} />
            <Route path="join/:inviteCode" element={<JoinGroup />} />
            <Route path="rides/:rideId" element={<Navigate to="/my-bookings?tab=driver" replace />} />
            <Route path="fcm-check" element={<FCMCheck />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </RouteErrorBoundary>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <GroupProvider>
            <ChatProvider>
              <ThemeToggle />
              <AppRoutes />
            </ChatProvider>
          </GroupProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
