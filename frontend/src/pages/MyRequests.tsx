import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Search, X } from 'lucide-react';
import { useGroup } from '../context/GroupContext';
import { useMyRequests } from './useMyRequests';
import type { ChipItem } from '../components/Chips/Chips';
import Chips from '../components/Chips/Chips';
import RideCard from '../components/RideCard/RideCard';
import ConfirmModal from '../components/ConfirmModal/ConfirmModal';
import ErrorBanner from '../components/ErrorBanner';
import { formatDateTimeNoSeconds } from '../utils/date';
import { getRideSourceLabel, getRequestStatusLabel } from '../utils/rideDisplay';
import HistorySection from '../components/HistorySection/HistorySection';
import { usePageTitle } from '../hooks/usePageTitle';
import styles from './MyRequests.module.css';

export default function MyRequests() {
  const navigate = useNavigate();
  const { t } = useTranslation(['rides', 'common', 'nav']);
  const pageTitle = t('nav:myRequests');
  usePageTitle(pageTitle);
  const { myGroups, activeChipId, setActiveChipId } = useGroup();

  const {
    requests,
    loading,
    error,
    requestToCancel,
    setRequestToCancel,
    cancelling,
    confirmCancelRequest,
  } = useMyRequests();

  const chipItems: ChipItem[] = useMemo(
    () => [
      { id: 'all', label: t('common:all') },
      { id: 'public', label: t('common:public') },
      ...myGroups.map((g) => ({ id: g.group_id, label: g.name })),
    ],
    [t, myGroups]
  );

  const displayedRequests = requests.filter((r) => {
    if (activeChipId === 'all') return true;
    if (activeChipId === 'public') return !r.group_id;
    return r.group_id === activeChipId;
  });
  const activeRequests = displayedRequests.filter((r) => r.status !== 'cancelled' && r.status !== 'completed' && r.status !== 'expired');
  const pastRequests = displayedRequests.filter((r) => r.status === 'cancelled' || r.status === 'completed' || r.status === 'expired');

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.pageLoading}>{t('common:loading')}</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1 className="sr-only">{pageTitle}</h1>
      <Chips items={chipItems} activeId={activeChipId} onChange={setActiveChipId} />

      {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}

      {displayedRequests.length === 0 ? (
        <div className={styles.emptyState}>
          <Search size={48} strokeWidth={1.5} className={styles.emptyIcon} />
          <h2 className={styles.emptyTitle}>{t('rides:myRequests_emptyTitle')}</h2>
          <p className={styles.emptySubtitle}>{t('rides:myRequests_emptySubtitle')}</p>
          <button
            type="button"
            className={styles.btnSearch}
            onClick={() => navigate('/search')}
          >
            <Search size={14} />
            {t('rides:searchTitle')}
          </button>
        </div>
      ) : (
        <>
          {activeRequests.length > 0 && (
            <>
              <div className={styles.sectionHeader}>
                <span className={styles.sectionLabel}>{t('rides:myRequests_activeLabel')}</span>
                <span className={styles.sectionCount}>
                  {t('rides:myRequests_activeCount', { count: activeRequests.length })}
                </span>
              </div>
              <div className={styles.gridWrap}>
                <div className={styles.grid}>
                  {activeRequests.map((r) => (
                    <div key={r.request_id} className={styles.cardWrap}>
                      <button
                        type="button"
                        className={styles.cardDeleteBtn}
                        onClick={() => setRequestToCancel(r)}
                        aria-label={t('rides:removeRequestAria')}
                        title={t('rides:removeRequestTitle')}
                      >
                        <X size={12} strokeWidth={2.5} />
                      </button>
                      <RideCard
                        originLabel={r.pickup_name ?? '?'}
                        destinationLabel={r.destination_name ?? '?'}
                        scheduleCaption={t('rides:requestScheduleCaption')}
                        time={formatDateTimeNoSeconds(r.requested_departure_time)}
                        status={getRequestStatusLabel(r.status)}
                        source={getRideSourceLabel(r.group_id, myGroups)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {pastRequests.length > 0 && (
            <div className={styles.gridWrap}>
              <HistorySection title={t('rides:myRequests_pastTitle', { count: pastRequests.length })}>
                <div className={styles.grid}>
                  {pastRequests.map((r) => (
                    <div key={r.request_id} className={styles.cardWrap}>
                      <RideCard
                        originLabel={r.pickup_name ?? '?'}
                        destinationLabel={r.destination_name ?? '?'}
                        scheduleCaption={t('rides:requestScheduleCaption')}
                        time={formatDateTimeNoSeconds(r.requested_departure_time)}
                        status={getRequestStatusLabel(r.status)}
                        source={getRideSourceLabel(r.group_id, myGroups)}
                      />
                    </div>
                  ))}
                </div>
              </HistorySection>
            </div>
          )}
        </>
      )}

      <ConfirmModal
        open={requestToCancel != null}
        onClose={() => setRequestToCancel(null)}
        title={t('rides:confirmCancelRequestTitle')}
        description={t('rides:confirmCancelRequestDescription')}
        confirmLabel={t('common:confirm')}
        variant="danger"
        loading={cancelling}
        onConfirm={confirmCancelRequest}
        titleId="confirm-cancel-request-title"
      />
    </div>
  );
}
