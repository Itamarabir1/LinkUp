import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getGroupByInviteCode, joinGroup } from '../api/groups';
import type { Group } from '../types/api';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { getApiErrorMessage, getApiStatus } from '../utils/apiError';
import styles from './JoinGroup.module.css';

export default function JoinGroup() {
  const { inviteCode } = useParams<{ inviteCode: string }>();
  const navigate = useNavigate();
  const [group, setGroup] = useState<Group | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    if (!inviteCode) {
      setLoading(false);
      setError('חסר קוד הזמנה.');
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError('');
    getGroupByInviteCode(inviteCode)
      .then((data) => {
        if (!cancelled) setGroup(data);
      })
      .catch(() => {
        if (!cancelled) {
          setError('הקבוצה לא נמצאה או שהקישור לא תקף.');
          setGroup(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [inviteCode]);

  const handleJoin = async () => {
    if (!inviteCode) return;
    setJoining(true);
    setError('');
    try {
      const joined = await joinGroup(inviteCode);
      if (joined?.group_id) {
        navigate(`/groups/${joined.group_id}`, { replace: true });
      } else {
        navigate('/', { replace: true });
      }
    } catch (err: unknown) {
      const status = getApiStatus(err);
      if (status === 409) {
        setError('אתה כבר חבר בקבוצה זו');
      } else if (status === 404) {
        setError('קוד ההצטרפות אינו תקף');
      } else {
        setError(getApiErrorMessage(err, 'הצטרפות לקבוצה נכשלה'));
      }
    } finally {
      setJoining(false);
    }
  };

  if (!inviteCode) {
    return (
      <div className={styles.page}>
        <p className={styles.pageError}>{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.pageLoading}>טוען...</div>
      </div>
    );
  }

  if (error || !group) {
    return (
      <div className={styles.page}>
        <h1 className={styles.pageTitle}>הצטרפות לקבוצה</h1>
        <ErrorBanner message={error || 'הקבוצה לא נמצאה.'} className={styles.pageError} />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>הצטרפות לקבוצה</h1>
      <div className={styles.card}>
        <div className={styles.groupName}>{group.name}</div>
        <div className={styles.memberCount}>
          {group.member_count != null ? `${group.member_count} חברים` : 'קבוצה פעילה'}
        </div>
        <LoadingButton
          type="button"
          className={`${styles.btn} ${styles.btnPrimary}`}
          loading={joining}
          loadingLabel="מצטרף..."
          onClick={handleJoin}
        >
          הצטרף לקבוצה
        </LoadingButton>
      </div>
    </div>
  );
}
