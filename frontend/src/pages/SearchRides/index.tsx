import { useAuth } from '../../context/AuthContext';
import { useGroup } from '../../context/GroupContext';
import { useTranslation } from 'react-i18next';
import { useSearchRides } from './useSearchRides';
import { SearchRidesForm } from './SearchRidesForm';
import { SearchRideCard } from './SearchRideCard';
import { usePageTitle } from '../../hooks/usePageTitle';
import styles from './SearchRides.module.css';

export default function SearchRides() {
  const { t } = useTranslation(['rides', 'nav']);
  const pageTitle = t('nav:searchRide');
  usePageTitle(pageTitle);
  const { user } = useAuth();
  const { myGroups } = useGroup();
  const s = useSearchRides();

  const activeGroupName = s.groupId
    ? myGroups.find((g) => g.group_id === s.groupId)?.name
    : null;

  return (
    <div className={styles.page}>
      <h1 className="sr-only">{pageTitle}</h1>
      {activeGroupName && (
        <div className={styles.groupBanner}>
          {t('rides:groupContext', { name: activeGroupName })}
        </div>
      )}
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>{t('rides:searchRideTitle')}</h1>
        <p className={styles.pageMeta}>{t('rides:searchMeta')}</p>
      </div>

      <SearchRidesForm
        error={s.error}
        pickup={s.pickup}
        setPickup={s.setPickup}
        destination={s.destination}
        setDestination={s.setDestination}
        searchRadius={s.searchRadius}
        setSearchRadius={s.setSearchRadius}
        selectedDate={s.selectedDate}
        setSelectedDate={s.setSelectedDate}
        locationLoading={s.locationLoading}
        searching={s.searching}
        onFillLocation={s.fillPickupFromMyLocation}
        onSwap={s.handleSwap}
        onSubmit={s.search}
        aiQuery={s.aiQuery}
        setAiQuery={s.setAiQuery}
        aiParsing={s.aiParsing}
        aiError={s.aiError}
        aiResult={s.aiResult}
        conversationHistory={s.conversationHistory}
        onParseAI={s.parseWithAI}
        onResetAI={s.resetAI}
      />

      <div className={styles.cardList}>
        {s.results.length === 0 && s.hasSearched && !s.searching ? (
          <div>
            <p className={styles.emptyText}>{t('rides:noSearchResults')}</p>
            {user && !s.alertSaved ? (
              <div style={{ textAlign: 'center' }}>
                <button
                  type="button"
                  className={`${styles.btn} ${styles.btnSuccess}`}
                  onClick={() => void s.saveAlert()}
                  disabled={s.savingAlert}
                >
                  {s.savingAlert ? t('rides:savingAlert') : t('rides:saveAlert')}
                </button>
              </div>
            ) : null}
            {s.alertSaved ? (
              <p className={styles.savedSearchBanner}>{t('rides:alertSaved')}</p>
            ) : null}
          </div>
        ) : (
          <>
            {s.results.length > 0 && (
              <div className={styles.resultsHeader}>
                <span className={styles.resultsLabel}>{t('rides:ridesFound', { count: s.results.length })}</span>
                {user && !s.alertSaved ? (
                  <button
                    type="button"
                    className={styles.saveAlertBtn}
                    onClick={() => void s.saveAlert()}
                    disabled={s.savingAlert}
                  >
                    {s.savingAlert ? t('rides:savingAlert') : t('rides:searchSaved')}
                  </button>
                ) : s.alertSaved ? (
                  <span className={styles.savedSearchBanner}>{t('rides:searchSaved')}</span>
                ) : null}
              </div>
            )}

            {s.results.map((r) => (
              <SearchRideCard
                key={r.ride_id}
                ride={r}
                driverInfo={s.driverInfoMap[r.ride_id]}
                loadingDriverRideId={s.loadingDriverRideId}
                sendingRequestRideId={s.sendingRequestRideId}
                requestSuccessRideId={s.requestSuccessRideId}
                requestErrorRideId={s.requestErrorRideId}
                requestErrorMessage={s.requestErrorMessage}
                onFetchDriver={s.fetchDriverInfo}
                onRequestJoin={s.sendRequestToJoin}
              />
            ))}

            {s.resultsHasMore && (
              <div className={styles.loadMoreWrap}>
                <button
                  type="button"
                  className={`${styles.btn} ${styles.btnOutline}`}
                  onClick={s.loadMoreResults}
                  disabled={s.loadingMore}
                >
                  {s.loadingMore ? t('rides:loadingMore') : t('rides:loadMore')}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
