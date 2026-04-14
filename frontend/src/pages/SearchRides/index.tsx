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
      {activeGroupName && (
        <div className={styles.groupBanner}>
          נוסע בשם קבוצה: {activeGroupName}
        </div>
      )}
      <h1 className={styles.pageTitle}>חפש טרמפ</h1>
      <p className={styles.pageMeta}>
        מוצא, יעד, רדיוס חיפוש וזמן יציאה — כמו בבקאנד.
      </p>

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
            <p className={styles.emptyText}>לא נמצאו נסיעות מתאימות.</p>
            {user && !s.alertSaved ? (
              <div style={{ textAlign: 'center' }}>
                <button
                  type="button"
                  className={`${styles.btn} ${styles.btnSuccess}`}
                  onClick={() => void s.saveAlert()}
                  disabled={s.savingAlert}
                >
                  {s.savingAlert ? 'שומר...' : 'התרע לי כשתופיע נסיעה מתאימה'}
                </button>
              </div>
            ) : null}
            {s.alertSaved ? (
              <p className={styles.savedSearchBanner}>נשמר! נודיע לך כשתופיע נסיעה מתאימה.</p>
            ) : null}
          </div>
        ) : (
          <>
            {s.results.length > 0 && (
              <div className={styles.resultsHeader}>
                <span className={styles.resultsLabel}>{s.results.length} נסיעות נמצאו</span>
                {user && !s.alertSaved ? (
                  <button
                    type="button"
                    className={styles.saveAlertBtn}
                    onClick={() => void s.saveAlert()}
                    disabled={s.savingAlert}
                  >
                    {s.savingAlert ? 'שומר...' : 'שמור חיפוש להתראות'}
                  </button>
                ) : s.alertSaved ? (
                  <span className={styles.savedSearchBanner}>החיפוש נשמר</span>
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
                  {s.loadingMore ? 'טוען...' : 'טען עוד נסיעות'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
