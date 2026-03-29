export interface ApiError {
  status: 'error';
  error_code: string;
  message: string;
  trace_id: string;
  details?: Record<string, unknown>;
}

/** Axios-style error body our backend returns (FastAPI). */
export type ApiErrorResponse = {
  response: {
    status: number;
    data: ApiError;
  };
};

export function isApiError(err: unknown): err is ApiErrorResponse {
  return (
    typeof err === 'object' &&
    err !== null &&
    'response' in err &&
    typeof (err as { response?: { status?: unknown; data?: { error_code?: unknown } } }).response
      ?.status === 'number' &&
    typeof (err as { response?: { data?: { error_code?: unknown } } }).response?.data?.error_code ===
      'string'
  );
}
