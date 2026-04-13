import { useAuth } from '../../context/AuthContext';
import { useGroup } from '../../context/GroupContext';
import { useSearchRides } from './useSearchRides';
import { SearchRidesForm } from './SearchRidesForm';
import { SearchRideCard } from './SearchRideCard';
import styles from './SearchRides.module.css';

export default function SearchRides() {
  const { user } = useAuth();
  const { myGroups } = useGroup();
  const s = useSearchRides();

  const activeGroupName = s.groupId
    ? myGroups.find((g) => g.group_id === s.groupId)?.name
    : null;

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>חפש טרמפ</h1>
      <p className={styles.pageMeta}>
        מוצא, יעד, רדיוס חיפוש (בק"מ) וזמן יציאה אופציונלי – כמו בבקאנד.
      </p>
      {activeGroupName ? (
        <div className={styles.groupBanner}>
          <span>🔍 מחפש נסיעות בקבוצה:</span>
          <strong>{activeGroupName}</strong>
        </div>
      ) : null}
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
      />
      <div className={styles.cardList}>
        {s.results.length === 0 && s.hasSearched && !s.searching ? (
          <div>
            <p className={`${styles.emptyText} ${styles.emptyTextTight}`}>
              לא נמצאו נסיעות מתאימות.
            </p>
            {user && !s.alertSaved ? (
              <div className={styles.saveAlertRowCenter}>
                <button
                  type="button"
                  className={`${styles.btn} ${styles.btnPrimary}`}
                  onClick={() => void s.saveAlert()}
                  disabled={s.savingAlert}
                >
                  {s.savingAlert ? 'שומר...' : '🔔 התרע לי כשתצא נסיעה מתאימה'}
                </button>
              </div>
            ) : null}
            {s.alertSaved ? (
              <p className={styles.savedSearchBanner}>
                ✅ נשמר! נודיע לך במייל כשתצא נסיעה מתאימה.
              </p>
            ) : null}
          </div>
        ) : (
          <>
            {s.results.length > 0 && user ? (
              <div className={styles.saveAlertRow}>
                {!s.alertSaved ? (
                  <button
                    type="button"
                    className={`${styles.btn} ${styles.btnOutline}`}
                    onClick={() => void s.saveAlert()}
                    disabled={s.savingAlert}
                  >
                    {s.savingAlert ? 'שומר...' : '🔔 שמור חיפוש זה להתראות'}
                  </button>
                ) : (
                  <p className={styles.savedSearchBanner}>✅ החיפוש נשמר להתראות</p>
                )}
              </div>
            ) : null}
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
            {s.resultsHasMore ? (
              <div className={styles.loadMoreWrap}>
                <button
                  type="button"
                  className={`${styles.btn} ${styles.btnOutline}`}
                  onClick={s.loadMoreResults}
                  disabled={s.loadingMore}
                >
                  {s.loadingMore ? 'טוען...' : 'טען עוד נסיעות'}
                </button>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
