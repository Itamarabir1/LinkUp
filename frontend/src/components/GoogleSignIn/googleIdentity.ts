/** Augments `window.google` for Google Identity Services (loaded at runtime). */
export {};

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
            itp_support?: boolean;
          }) => void;
          renderButton: (
            element: HTMLElement,
            config: { theme?: string; size?: string; text?: string; width?: number; locale?: string }
          ) => void;
          prompt: (
            callback?: (notification: {
              isNotDisplayed: boolean;
              isSkippedMoment: boolean;
              dismissedMoment?: number;
              skippedMoment?: number;
            }) => void
          ) => void;
          disableAutoSelect: () => void;
        };
      };
    };
  }
}
