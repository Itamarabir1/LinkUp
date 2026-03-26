/**
 * buildOptions — shared k6 scenario config for all load scripts.
 *
 * Modes:
 *   1. Manual:  k6 run -e VUS=50 -e DURATION=1m <script>
 *   2. Stages:   k6 run <script>  (no VUS/DURATION — uses defaultStages)
 */
export function buildOptions(thresholds, defaultStages) {
  const VUS = parseInt(__ENV.VUS) || null;
  const DURATION = __ENV.DURATION || null;

  if (VUS && DURATION) {
    return {
      vus: VUS,
      duration: DURATION,
      thresholds,
    };
  }

  return {
    stages: defaultStages,
    thresholds,
  };
}
