export interface ApiError {
  status: 'error';
  error_code: string;
  message: string;
  trace_id: string;
  details?: Record<string, unknown>;
}

export function isApiError(err: unknown): err is { response: { data: ApiError } } {
  return (
    typeof err === 'object' &&
    err !== null &&
    'response' in err &&
    typeof (err as { response?: { data?: { error_code?: unknown } } }).response?.data?.error_code ===
      'string'
  );
}
