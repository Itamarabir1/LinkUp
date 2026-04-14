import { useNavigate } from 'react-router-dom';
import { Users, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useGroup } from '../context/GroupContext';
import ErrorBanner from '../components/ErrorBanner';
import { useAuth } from '../context/AuthContext';
import styles from './Groups.module.css';

const AVATAR_COLORS = [
  { bg: '#E1F5EE', text: '#0F6E56' },
  { bg: '#EEEDFE', text: '#534AB7' },
  { bg: '#FEF3C7', text: '#92400E' },
  { bg: '#FCE7F3', text: '#9D174D' },
  { bg: '#E0F2FE', text: '#0369A1' },
];

function getAvatarStyle(index: number) {
  const c = AVATAR_COLORS[index % AVATAR_COLORS.length];
  return { backgroundColor: c.bg, color: c.text };
}

export default function Groups() {
  const { t } = useTranslation(['groups', 'common']);
  const navigate = useNavigate();
  const { user } = useAuth();
  const { myGroups, isLoadingGroups, groupsError } = useGroup();

  const handleCreateGroup = () => navigate('/groups/new');

  if (isLoadingGroups) {
    return (
      <div className={styles.page}>
        <div className={styles.pageLoading}>{t('common:loading')}</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {groupsError ? <ErrorBanner message={groupsError} /> : null}
      <header className={styles.pageHeader}>
        <button
          type="button"
          className={styles.btnPrimary}
          onClick={handleCreateGroup}
        >
          <Plus size={14} />
          {t('groups:createGroup')}
        </button>
      </header>

      {myGroups.length === 0 ? (
        <div className={styles.emptyState}>
          <Users size={48} strokeWidth={1.5} className={styles.emptyIcon} />
          <h2 className={styles.emptyTitle}>{t('groups:noGroupsYet')}</h2>
          <p className={styles.emptySubtitle}>{t('groups:createOrJoin')}</p>
        </div>
      ) : (
        <div className={styles.grid}>
          {myGroups.map((g, index) => {
            const isAdmin = g.admin_id === user?.user_id;
            const avatarStyle = getAvatarStyle(index);
            return (
              <article
                key={g.group_id}
                className={styles.card}
                onClick={() => navigate(`/groups/${g.group_id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigate(`/groups/${g.group_id}`);
                  }
                }}
              >
                <div className={styles.cardTop}>
                  {g.avatar_url ? (
                    <img
                      src={g.avatar_url}
                      alt=""
                      className={styles.avatarImg}
                    />
                  ) : (
                    <div
                      className={styles.avatar}
                      style={avatarStyle}
                    >
                      {g.name.charAt(0)}
                    </div>
                  )}
                  <div className={styles.cardInfo}>
                    <button
                      type="button"
                      className={styles.groupNameBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/groups/${g.group_id}`);
                      }}
                    >
                      {g.name}
                    </button>
                    <span className={styles.memberCount}>
                      {t('groups:membersLabel', { count: g.member_count ?? 0 })}
                    </span>
                  </div>
                </div>
                {g.description && (
                  <p className={styles.cardDescription}>{g.description}</p>
                )}
                <div className={styles.cardFooter}>
                  {isAdmin && (
                    <span className={styles.badgeAdmin}>{t('groups:admin')}</span>
                  )}
                  <span className={styles.badgeType}>{t('groups:privateGroup')}</span>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
