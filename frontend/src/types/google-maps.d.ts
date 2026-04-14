/* Minimal types for Google Maps JavaScript API (loaded via script tag) */
declare namespace google {
  namespace maps {
    namespace event {
      function trigger(instance: unknown, eventName: string): void;
    }
    enum SymbolPath {
      CIRCLE,
    }
    interface Symbol {
      path: SymbolPath;
      scale?: number;
      fillColor?: string;
      fillOpacity?: number;
      strokeColor?: string;
      strokeWeight?: number;
    }
    class Map {
      constructor(mapDiv: HTMLElement, opts?: MapOptions);
      fitBounds(bounds: LatLngBounds, padding?: number | Padding): void;
      setCenter(center: LatLngLiteral): void;
      panTo?(point: LatLngLiteral): void;
    }
    interface MapOptions {
      zoom?: number;
      center?: LatLngLiteral;
      mapTypeControl?: boolean;
      streetViewControl?: boolean;
      fullscreenControl?: boolean;
      zoomControl?: boolean;
    }
    interface LatLngLiteral {
      lat: number;
      lng: number;
    }
    class LatLngBounds {
      extend(point: LatLngLiteral): void;
      isEmpty(): boolean;
    }
    class Polyline {
      constructor(opts?: PolylineOptions);
    }
    interface PolylineOptions {
      path?: LatLngLiteral[];
      geodesic?: boolean;
      strokeColor?: string;
      strokeOpacity?: number;
      strokeWeight?: number;
      map?: Map;
    }
    class Marker {
      constructor(opts?: MarkerOptions);
      setMap(map: Map | null): void;
      setPosition(position: LatLngLiteral): void;
      setVisible(visible: boolean): void;
    }
    interface MarkerOptions {
      position?: LatLngLiteral;
      map?: Map;
      title?: string;
      label?: { text: string; color: string };
      icon?: Symbol;
    }
    interface Padding {
      top?: number;
      right?: number;
      bottom?: number;
      left?: number;
    }

    /** Advanced markers (`marker` library); loaded with Maps JS API. */
    namespace marker {
      interface AdvancedMarkerElementOptions {
        map?: Map | null;
        position?: LatLngLiteral;
        title?: string;
        content?: HTMLElement;
      }
      class AdvancedMarkerElement {
        map: Map | null;
        position?: LatLngLiteral;
        constructor(opts?: AdvancedMarkerElementOptions);
      }
    }
  }
}
