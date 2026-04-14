import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { getGroupByInviteCode, joinGroup } from '../api/groups';
import type { Group } from '../types/api';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { getApiErrorMessage, getApiStatus } from '../utils/apiError';
import styles from './JoinGroup.module.css';

export default function JoinGroup() {
  const { t } = useTranslation(['groups', 'common']);
  const { inviteCode } = useParams<{ inviteCode: string }>();
  const navigate = useNavigate();
  const [group, setGroup] = useState<Group | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    if (!inviteCode) {
      setLoading(false);
      setError(t('groups:missingInviteCode'));
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
          setError(t('groups:groupNotFoundOrInvalid'));
          setGroup(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [inviteCode, t]);

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
        setError(t('groups:alreadyMember'));
      } else if (status === 404) {
        setError(t('groups:invalidJoinCode'));
      } else {
        setError(getApiErrorMessage(err, t('groups:joinFailed')));
      }
    } finally {
      setJoining(false);
    }
  };

  if (!inviteCode) {
    return (
      <div className={styles.page}>
        <div className={styles.inner}>
          <ErrorBanner message={error || t('groups:missingInviteCode')} className={styles.pageError} />
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.inner}>
          <div className={styles.pageLoading}>{t('common:loading')}</div>
        </div>
      </div>
    );
  }

  if (error || !group) {
    return (
      <div className={styles.page}>
        <div className={styles.inner}>
          <h1 className={styles.pageTitle}>{t('groups:joinGroupTitle')}</h1>
          <ErrorBanner
            message={error || t('common:not_found')}
            className={styles.pageError}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        <h1 className={styles.pageTitle}>{t('groups:joinGroupTitle')}</h1>
        <div className={styles.card}>
          {group.avatar_url ? (
            <img
              src={group.avatar_url}
              alt={group.name}
              className={styles.groupAvatarImg}
            />
          ) : (
            <div className={styles.groupAvatar}>
              {group.name.charAt(0).toUpperCase()}
            </div>
          )}

          <div className={styles.groupName}>{group.name}</div>

          <div className={styles.groupMeta}>
            {group.member_count != null && (
              <span>{t('groups:membersLabel', { count: group.member_count })}</span>
            )}
            {group.member_count != null && (
              <span className={styles.metaDot} />
            )}
            <span>{t('groups:privateGroupLabel')}</span>
          </div>

          {error && (
            <ErrorBanner message={error} className={styles.pageError} />
          )}

          <LoadingButton
            type="button"
            className={styles.btnPrimary}
            loading={joining}
            loadingLabel={t('groups:joiningButton')}
            onClick={handleJoin}
          >
            {t('groups:joinButton')}
          </LoadingButton>
        </div>
      </div>
    </div>
  );
}
