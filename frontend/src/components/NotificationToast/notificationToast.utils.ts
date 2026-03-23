export interface ToastData {
  title: string;
  body: string;
}

let showToastFn: ((data: ToastData) => void) | null = null;

export function triggerNotificationToast(data: ToastData): void {
  showToastFn?.(data);
}

export function setShowToastFn(fn: ((data: ToastData) => void) | null): void {
  showToastFn = fn;
}
