/**
 * צליל התראה — קובץ סטטי ב-public (Mixkit WAV; אפשר להחליף ב-notification.mp3 אחרי המרה).
 */
export function playNotificationChime(): void {
  try {
    const audio = new Audio('/notification.wav');
    audio.volume = 0.5;
    void audio.play();
  } catch {
    // ignore — autoplay policy
  }
}
