import { Link } from 'react-router-dom';

export default function AdminHome() {
  return (
    <div>
      <p>Welcome to the admin panel.</p>
      <p>
        <Link to="/admin/health">Health dashboard →</Link>
      </p>
    </div>
  );
}
