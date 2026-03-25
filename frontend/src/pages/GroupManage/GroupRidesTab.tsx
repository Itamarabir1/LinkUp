import Chips from '../../components/Chips/Chips';
import RideCard from '../../components/RideCard/RideCard';
import { formatRideDate } from '../../utils/date';
import { getRideStatusLabel } from './groupManage.utils';
import type { GroupManageViewModel } from './useGroupManage';
import styles from './GroupManage.module.css';

export default function GroupRidesTab({ vm }: { vm: GroupManageViewModel }) {
  return (
    <>
      <Chips items={vm.dateChipItems} activeId={vm.dateChip} onChange={vm.setDateChip} />
      {vm.loadingRides ? (
        <div className={styles.pageLoading}>טוען נסיעות...</div>
      ) : vm.displayedRides.length === 0 ? (
        <div className={styles.emptyState}>
          <p className={styles.emptyText}>אין נסיעות בקבוצה בתקופה הזו.</p>
        </div>
      ) : (
        <div className={styles.ridesGrid}>
          {vm.displayedRides.map((r) => (
            <RideCard
              key={r.ride_id}
              route={`${r.origin_name ?? '?'} ← ${r.destination_name ?? '?'}`}
              time={formatRideDate(r.departure_time)}
              status={getRideStatusLabel(r)}
            />
          ))}
        </div>
      )}
    </>
  );
}
