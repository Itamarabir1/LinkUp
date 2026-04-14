# RideCard, Chips, HistorySection — Phased Integration

Execute phases in order. Run smoke test after each phase before continuing.

---

## PHASE A — Token improvements only (zero risk)

File: `frontend/src/components/RideCard/RideCard.module.css`

Replace ONLY these specific rules — do not touch layout, spacing, or ::before:

```css
/* Replace transition */
transition: box-shadow 200ms ease, transform 200ms ease, border-color 200ms ease;
/* WITH */
transition: box-shadow var(--transition-fast), transform var(--transition-fast), border-color var(--transition-fast);

/* Replace font-family strings */
font-family: "Heebo", sans-serif;
/* WITH */
font-family: var(--font-primary, "Heebo", sans-serif);
```

Apply the font-family replacement to ALL rules in the file that contain it
(.route, .scheduleCaption, .time, .badge, .source).

**Smoke test:** MyRides, MyRequests, GroupRidesTab — no visual change expected.

---

## PHASE B — Status rail + data-status (controlled visual upgrade)

### `frontend/src/components/RideCard/RideCard.tsx`

Replace the entire file with the new draft. Key changes:
- Adds `data-status={variant}` attribute to `<article>`
- Restores `toLowerCase().trim()` normalization in `getStatusVariant`
- All existing props unchanged

Verify `getStatusVariant` contains:
```ts
const s = status.toLowerCase().trim();
```

### `frontend/src/components/RideCard/RideCard.module.css`

Replace entire file with new draft. Key additions:
- `position: relative; overflow: hidden` on `.card`
- `::before` pseudo-element for status accent bar (right side, 3px wide)
- `[data-status="success"]::before`, `[data-status="warning"]::before` etc.
- `display: flex; flex-direction: column` on `.card`
- `margin-top: auto` + `border-top` on `.footer`
- `.source` gets subtle pill style

**Status mapping to verify on each screen:**

| Screen | Status strings produced | Expected variant |
|---|---|---|
| MyRides | "פעילה", "1 מקום", "3 מקומות", "מלא", "בוטלה" | success, success, success, warning, danger |
| MyRequests | "מחפש", "ממתין לאישור", "אושר", "נדחה", "הושלם", "פג תוקף", "נמצאה נסיעה", "בוטל" | info, warning, success, danger, success, neutral, success, danger |

**Smoke test:**
- [ ] Each card shows correct color accent bar
- [ ] Route text does not truncate unexpectedly on narrow screens
- [ ] Footer badge and source pill readable in both light/dark mode
- [ ] Hover lift effect works

---

## PHASE C — Chips (selective merge)

File: `frontend/src/components/Chips/Chips.module.css`

Replace entire file with new draft.

Changes:
- Removes `border-bottom` and `background` from `.wrap` (these belonged to old page layout, not the chip component)
- Removes `scrollbar-width: none` + webkit scrollbar hide
- Token-based transitions
- `.chipSelected` border upgraded to `1.5px`

**Important:** After merging, check `MyRides` and `MyRequests` page padding.
The chips wrap no longer has a background — the page background shows through.
This is intentional. If alignment looks off, add `padding: 16px 24px` to
`.page` in `MyRides.module.css` and `MyRequests.module.css`.

**Smoke test:**
- [ ] Chips scroll horizontally on narrow screens
- [ ] Active chip shows Indigo highlight
- [ ] No layout shift on MyRides / MyRequests / group pages

---

## PHASE D — HistorySection

File: `frontend/src/components/HistorySection/HistorySection.module.css`

Replace entire file with new draft.

**Critical:** The new draft does NOT include `opacity: 0.6` on `.body`.
Verify this before merging — the `.body` rule must be:
```css
.body {
  margin-top: 4px;
}
```

Changes:
- Toggle button becomes uppercase label style (matches section-label pattern)
- Token-based transition and font
- No opacity on body content

**Smoke test:**
- [ ] History section toggle works (open/close)
- [ ] History cards fully readable — no fading
- [ ] Toggle label legible in dark mode

---

## PHASE E — Validation gate

Manual QA across all affected screens:

### MyRides
- [ ] Active rides grid renders correctly (3 columns → 2 → 1)
- [ ] Status accent bar correct color per ride
- [ ] Delete button hidden until hover (visible on touch/focus)
- [ ] History section toggles, cards readable

### MyRequests
- [ ] Same grid and delete button behavior
- [ ] Status variants correct for all request states
- [ ] History section works

### GroupRidesTab
- [ ] RideCard renders without errors
- [ ] No prop changes needed (GroupRidesTab uses same RideCard props)

### MyBookings (indirect)
- [ ] HistorySection still toggles in both PassengerBookingsTab and DriverBookingsTab

### RTL
- [ ] All cards right-aligned
- [ ] Accent bar on RIGHT side (not left)
- [ ] Source pill does not overflow

### Lint
```bash
cd frontend && npx eslint src/components/RideCard/RideCard.tsx src/components/Chips/Chips.module.css --max-warnings 0
```

---

## Do NOT change
- `Chips.tsx` — no TSX changes needed
- `HistorySection.tsx` — no TSX changes needed
- `MyRides.tsx` — no changes needed
- `MyRequests.tsx` — no changes needed
- Any booking or group files
