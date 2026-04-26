/**
 */
export function playNotificationChime(): void {
  const audio = new Audio('/notification.wav');
  audio.volume = 0.5;
  void audio.play().catch(() => {
    // Ignore browser autoplay restrictions or missing device output.
  });
}
