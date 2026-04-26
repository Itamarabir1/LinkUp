/**
 */
export function playNotificationChime(): void {
  try {
    const audio = new Audio('/notification.wav');
    audio.volume = 0.5;
    void audio.play();
  } catch {
  }
}
