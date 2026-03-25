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
        מוצא, יעד, רדיוס חיפוש (מטרים) וזמן יציאה אופציונלי – כמו בבקאנד.
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
        {s.results.length === 0 && s.pickup && s.destination && !s.searching ? (
          <div>
            <p className={`${styles.emptyText} ${styles.emptyTextTight}`}>
              לא נמצאו נסיעות.
            </p>
            {user ? (
              <p className={styles.savedSearchBanner}>
                ✅ פרטי החיפוש שלך נשמרו ותקבל התראות כאשר יימצאו נסיעות מתאימות.
              </p>
            ) : null}
          </div>
        ) : (
          <>
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
