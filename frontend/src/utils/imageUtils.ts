/**
 */
export interface CompressOptions {
  maxWidth: number;
  quality: number;
}

export function compressImage(file: File, options: CompressOptions): Promise<Blob> {
  const { maxWidth, quality } = options;
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      const w = img.naturalWidth;
      const h = img.naturalHeight;
      let targetW = w;
      let targetH = h;
      if (w > maxWidth || h > maxWidth) {
        if (w >= h) {
          targetW = maxWidth;
          targetH = Math.round((h * maxWidth) / w);
        } else {
          targetH = maxWidth;
          targetW = Math.round((w * maxWidth) / h);
        }
      }
      const canvas = document.createElement('canvas');
      canvas.width = targetW;
      canvas.height = targetH;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Canvas context not available'));
        return;
      }
      ctx.drawImage(img, 0, 0, targetW, targetH);
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);
          else reject(new Error('toBlob failed'));
        },
        'image/webp',
        Math.min(1, Math.max(0, quality))
      );
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image'));
    };
    img.src = url;
  });
}
