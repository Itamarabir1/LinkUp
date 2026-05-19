import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { enUS, he } from 'date-fns/locale';
import { forwardRef } from 'react';
import { useTranslation } from 'react-i18next';
import { formatDurationMinutes } from '../utils/duration';
import {
  MapPin,
  ArrowUpDown,
  ChevronRight,
  Map,
  Calendar,
  Sparkles,
  RotateCcw,
  Bot,
} from 'lucide-react';
import LoadingButton from '../components/LoadingButton';
import RouteMapModal from '../components/RouteMapModal';
import { useGroup } from '../context/GroupContext';
import { useLang } from '../context/LangContext';
import { useCreateRide } from './useCreateRide';
import styles from './CreateRide.module.css';

interface DateTriggerProps {
  value?: string;
  onClick?: () => void;
  displayText: string;
}

const DateTrigger = forwardRef<HTMLButtonElement, DateTriggerProps>(
  ({ onClick, displayText }, ref) => (
    <button
      type="button"
      ref={ref}
      onClick={onClick}
      className={styles.datetimeTrigger}
      aria-label={displayText}
    >
      <Calendar size={14} strokeWidth={2} className={styles.datetimeIcon} />
      <span>{displayText}</span>
    </button>
  )
);

function StepIndicator({ step, step1Label, step2Label }: { step: 1 | 2; step1Label: string; step2Label: string }) {
  return (
    <div className={styles.stepsRow}>
      <div className={styles.stepItem}>
        <div className={`${styles.stepCircle} ${step === 1 ? styles.active : styles.done}`}>
          {step === 1 ? '1' : '✓'}
        </div>
        <span className={`${styles.stepLabel} ${step === 1 ? styles.active : styles.idle}`}>
          {step1Label}
        </span>
      </div>
      <div className={`${styles.stepLine} ${step === 2 ? styles.done : ''}`} />
      <div className={styles.stepItem}>
        <div className={`${styles.stepCircle} ${step === 2 ? styles.active : styles.idle}`}>
          2
        </div>
        <span className={`${styles.stepLabel} ${step === 2 ? styles.active : styles.idle}`}>
          {step2Label}
        </span>
      </div>
    </div>
  );
}

export default function CreateRide() {
  const { lang } = useLang();
  const { t } = useTranslation(['rides', 'common']);
  const { myGroups } = useGroup();
  const {
    groupId,
    originName,
    setOriginName,
    destinationName,
    setDestinationName,
    selectedDate,
    setSelectedDate,
    seats,
    setSeats,
    loading,
    preview,
    selectedRouteIndex,
    setSelectedRouteIndex,
    creating,
    error,
    locationLoading,
    mapPreviewData,
    setMapPreviewData,
    fillOriginFromMyLocation,
    handleSwap,
    requestPreview,
    createRide,
    aiQuery,
    setAiQuery,
    aiParsing,
    aiError,
    aiResult,
    aiFollowUp,
    conversationHistory,
    parseWithAI,
    resetAI,
  } = useCreateRide();

  const activeGroupName = groupId
    ? myGroups.find((g) => g.group_id === groupId)?.name
    : null;

  const hasPreview = preview && (preview.routes?.length ?? 0) > 0;
  const currentStep: 1 | 2 = hasPreview ? 2 : 1;

  const formatDateDisplay = (date: Date) => {
    const locale = lang === 'en' ? 'en-US' : 'he-IL';
    const now = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(now.getDate() + 1);
    const timeStr = date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
    if (date.toDateString() === now.toDateString()) return `${t('common:today')}, ${timeStr}`;
    if (date.toDateString() === tomorrow.toDateString()) return `${t('common:tomorrow')}, ${timeStr}`;
    return date.toLocaleDateString(locale, { day: 'numeric', month: 'short' }) + `, ${timeStr}`;
  };

  return (
    <div className={styles.page}>
      <a href={groupId ? `/groups/${groupId}` : '/my-rides'} className={styles.backLink}>
        <ChevronRight size={14} />
        {groupId ? t('rides:backToGroup') : t('rides:backToRides')}
      </a>

      <StepIndicator step={currentStep} step1Label={t('rides:step1Label')} step2Label={t('rides:step2Label')} />

      {!hasPreview && (
        <>
          <div className={styles.pageHeader}>
            {activeGroupName && (
              <div className={styles.groupPill}>
                <span className={styles.groupPillDot} />
                {t('rides:groupContext', { name: activeGroupName })}
              </div>
            )}
            <h1 className={styles.pageTitle}>{t('rides:whereAreYouGoing')}</h1>
            <p className={styles.pageMeta}>
              {t('rides:fillRouteAndTime')}
            </p>
          </div>

          {/* ══ AI Ride Creation Assistant ══ */}
          <div className={styles.aiBlock}>
            <div className={styles.aiHeader}>
              <div className={styles.aiHeaderLeft}>
                <Sparkles
                  size={13}
                  strokeWidth={2.5}
                  className={styles.aiSparkle}
                  aria-hidden
                />
                <span className={styles.aiTitle}>
                  {t('rides:aiCreateTitle')}
                </span>
              </div>
              {(aiResult !== null || conversationHistory.length > 0) && (
                <button
                  type="button"
                  className={styles.aiResetBtn}
                  onClick={resetAI}
                  disabled={aiParsing}
                  aria-label={t('rides:aiCreateReset')}
                  title={t('rides:aiCreateReset')}
                >
                  <RotateCcw size={11} strokeWidth={2.5} aria-hidden />
                </button>
              )}
            </div>

            {conversationHistory.length > 0 && aiFollowUp && (
              <div className={styles.aiHistory}>
                {conversationHistory.map((turn, i) => (
                  <div
                    key={`${turn.role}-${i}-${turn.content.slice(0, 24)}`}
                    className={
                      turn.role === 'user'
                        ? styles.aiHistoryUser
                        : styles.aiHistoryAssistant
                    }
                  >
                    {turn.content}
                  </div>
                ))}
              </div>
            )}

            <div className={styles.aiInputRow}>
              <textarea
                className={`${styles.aiTextarea}${
                  aiParsing ? ` ${styles.aiTextareaParsing}` : ''
                }`}
                placeholder={aiFollowUp ?? t('rides:aiCreatePlaceholder')}
                value={aiQuery}
                onChange={(e) => setAiQuery(e.target.value)}
                rows={2}
                maxLength={400}
                dir="auto"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    void parseWithAI();
                  }
                }}
              />
              <button
                type="button"
                className={styles.aiSendBtn}
                onClick={() => void parseWithAI()}
                disabled={aiParsing || !aiQuery.trim()}
                aria-label={t('rides:aiCreateParseBtn')}
                title={t('rides:aiCreateParseBtn')}
              >
                {aiParsing ? (
                  <span className={styles.aiSpinner} aria-hidden />
                ) : (
                  <>
                    <Sparkles size={14} strokeWidth={2} aria-hidden />
                    <span>{t('rides:aiCreateParseBtn')}</span>
                  </>
                )}
              </button>
            </div>

            {aiFollowUp && !aiError && (
              <div className={styles.aiFollowUp} role="status" aria-live="polite">
                <Bot
                  size={14}
                  strokeWidth={2}
                  className={styles.aiFollowUpIcon}
                  aria-hidden
                />
                <span>{aiFollowUp}</span>
              </div>
            )}

            {aiError && (
              <p className={styles.aiErrorMsg} role="alert">
                {aiError}
              </p>
            )}

            <div className={styles.aiDivider}>
              <span className={styles.aiDividerLabel}>
                {t('rides:aiCreateDivider')}
              </span>
            </div>
          </div>

          <form onSubmit={requestPreview}>
            {error ? <div className={styles.pageError}>{error}</div> : null}

            <div className={styles.formBlock}>
              <div className={styles.routeSection}>
                <div className={styles.fieldRow}>
                  <div className={`${styles.fieldIcon} ${styles.origin}`}>
                    <MapPin size={15} strokeWidth={2.5} />
                  </div>
                  <div className={styles.fieldContent}>
                    <div className={styles.fieldLabel}>{t('rides:origin')}</div>
                    <input type="text" className={styles.formInput} placeholder={t('rides:originPlaceholder')}
                      value={originName} onChange={(e) => setOriginName(e.target.value)} autoComplete="off" />
                  </div>
                  <button type="button" className={styles.gpsBtn}
                    onClick={fillOriginFromMyLocation} disabled={locationLoading} title={t('rides:myLocation')}>
                    {locationLoading ? '...' : 'GPS'}
                  </button>
                </div>

                <div className={styles.fieldDivider}>
                  <div className={styles.swapWrap}>
                    <button type="button" className={styles.swapBtn} onClick={handleSwap} aria-label={t('rides:swapDirection')}>
                      <ArrowUpDown size={13} strokeWidth={2} />
                    </button>
                  </div>
                </div>

                <div className={styles.fieldRow}>
                  <div className={`${styles.fieldIcon} ${styles.dest}`}>
                    <MapPin size={15} strokeWidth={2} />
                  </div>
                  <div className={styles.fieldContent}>
                    <div className={styles.fieldLabel}>{t('rides:destination')}</div>
                    <input type="text" className={styles.formInput} placeholder={t('rides:destinationPlaceholder')}
                      value={destinationName} onChange={(e) => setDestinationName(e.target.value)} autoComplete="off" />
                  </div>
                </div>
              </div>

              <div className={styles.metaRow}>
                <div className={styles.metaField}>
                  <div className={styles.metaLabel}>{t('rides:availableSeats')}</div>
                  <div className={styles.metaValue}>
                    <div className={styles.seatsControl}>
                      <button type="button" className={styles.seatBtn}
                        onClick={() => setSeats((s) => Math.max(1, s - 1))} disabled={seats <= 1}>−</button>
                      <span className={styles.seatsValue}>{seats}</span>
                      <button type="button" className={styles.seatBtn}
                        onClick={() => setSeats((s) => Math.min(8, s + 1))} disabled={seats >= 8}>+</button>
                    </div>
                    <span className={styles.seatsUnit}>{t('rides:passengers')}</span>
                  </div>
                </div>

                <div className={styles.metaField}>
                  <div className={styles.metaLabel}>{t('rides:departureTime')}</div>
                  <DatePicker
                    selected={selectedDate}
                    onChange={(date: Date | null) => date && setSelectedDate(date)}
                    showTimeSelect timeFormat="HH:mm" timeIntervals={15}
                    dateFormat="dd/MM/yyyy HH:mm" locale={lang === 'en' ? enUS : he} minDate={new Date()}
                    wrapperClassName={styles.datetimeWrapper}
                    customInput={<DateTrigger displayText={formatDateDisplay(selectedDate)} />}
                  />
                </div>
              </div>

              <LoadingButton type="submit" className={`${styles.btn} ${styles.btnPrimary}`}
                loading={loading} loadingLabel={t('rides:calculatingRoutes')}>
                {t('rides:previewButton')}
              </LoadingButton>
            </div>
          </form>
        </>
      )}

      {preview && (preview.routes?.length ?? 0) === 0 && (
        <p className={styles.routesEmptyHint}>{t('rides:noRoutes')}</p>
      )}

      {hasPreview && (
        <>
          <div className={styles.pageHeader}>
            <h1 className={styles.pageTitle}>{t('rides:selectRoute')}</h1>
            <p className={styles.pageMeta}>{t('rides:ridesFound', { count: preview.routes!.length })}</p>
          </div>

          {error ? <div className={styles.pageError}>{error}</div> : null}

          <div className={styles.sectionLabel}>{t('rides:availableRoutes')}</div>

          <div className={styles.routeOptions}>
            {preview.routes!.map((route, idx) => (
              <div key={route.route_index} role="button" tabIndex={0}
                className={`${styles.routeOption} ${selectedRouteIndex === route.route_index ? styles.routeOptionSelected : ''}`}
                onClick={() => setSelectedRouteIndex(route.route_index)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedRouteIndex(route.route_index); } }}>
                <div className={styles.routeOptionContent}>
                  <div className={styles.cardRoute}>
                    {t('rides:routeNumber', { number: route.route_index + 1 })}{route.summary ? ` — ${route.summary}` : ''}
                  </div>
                  <div className={styles.cardMeta}>
                    <span>{route.distance_km ?? 0} {t('rides:km')}</span>
                    <span className={styles.routeMetaDot} />
                    <span>{formatDurationMinutes(route.duration_min ?? 0)}</span>
                    {idx === 0 && (<><span className={styles.routeMetaDot} /><span className={styles.routeFastest}>{t('rides:fastestRoute')}</span></>)}
                  </div>
                </div>
                <button type="button" className={styles.btnRouteMap}
                  onClick={(e) => { e.stopPropagation(); setMapPreviewData({ originCoords: preview.origin_coords, destinationCoords: preview.destination_coords, routeCoords: route.coords ?? [], summary: route.summary || '' }); }}>
                  <Map size={12} style={{ display: 'inline', marginLeft: 4 }} />{t('rides:map')}
                </button>
                <div className={styles.routeSelIndicator}>
                  {selectedRouteIndex === route.route_index && (
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#fff' }} />
                  )}
                </div>
              </div>
            ))}
          </div>

          <p className={styles.routeHint}>{t('rides:routeHint')}</p>

          <RouteMapModal data={mapPreviewData} onClose={() => setMapPreviewData(null)} />

          <LoadingButton type="button" className={`${styles.btn} ${styles.btnSuccess}`}
            loading={creating} loadingLabel={t('rides:creatingRide')} onClick={createRide}>
            {t('rides:createButton')}
          </LoadingButton>
        </>
      )}
    </div>
  );
}
