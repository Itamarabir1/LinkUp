let loadPromise: Promise<void> | null = null;

export function loadGoogleMaps(
  apiKey: string,
  onLoad: () => void,
  onError: () => void
): void {
  if (window.google?.maps) {
    onLoad();
    return;
  }

  if (loadPromise) {
    loadPromise
      .then(onLoad)
      .catch(onError);
    return;
  }

  loadPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Google Maps'));
    document.head.appendChild(script);
  });

  loadPromise
    .then(onLoad)
    .catch(() => {
      loadPromise = null;
      onError();
    });
}
