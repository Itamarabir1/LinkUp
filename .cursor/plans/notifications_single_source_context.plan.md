---
name: ""
overview: ""
todos: []
isProject: false
---

# איחוד התראות — אפשרות A (מקור אמת ב־ChatContext)

## סטטוס

המלצה סופית מאושרת; **לא בוצע בקוד** עד לפקודת יישום מפורשת.

## הבעיה (סיכום)

1. **כפל GET בכניסה למסך:** `useNotifications` קורא `fetchMyNotifications` ואז `refreshUnreadNotifications()` — שוב אותו endpoint.
2. **כפל מ־WebSocket:** `refreshUnreadNotifications()` + אירוע `linkup-notifications-refresh` שמפעיל `fetchNotifications` — עד שלוש קריאות זהות מאירוע אחד כשהמסך פתוח.

## גישה נבחרת: אפשרות A

חשיפת `notificationList` מ־`ChatContext` והסרת fetch/listener כפול מ־`useNotifications`.

### שינויים בקבצים


| קובץ                                                                                     | פעולה                                                                                                                                           |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `[frontend/src/context/chatContext.types.ts](frontend/src/context/chatContext.types.ts)` | ייבוא `NotificationItem`; הוספת `notificationList: NotificationItem[]` ל־`ChatContextValue`                                                     |
| `[frontend/src/context/ChatContext.tsx](frontend/src/context/ChatContext.tsx)`           | ב־`useMemo` value: `notificationList: state.notificationList`; בתלויות: `state.notificationList`                                                |
| `[frontend/src/pages/useNotifications.ts](frontend/src/pages/useNotifications.ts)`       | הסרת `fetchMyNotifications`, state מקומי לרשימה, `fetchNotifications`, שני ה־`useEffect` לטעינה/אירוע; שימוש ב־`notificationList` מ־`useChat()` |


### מה נמחק מ־`useNotifications.ts`

- `import fetchMyNotifications`
- `useState` ל־`list` (ול־`loading` / `error` אם מוחלפים — ראו הערות)
- `fetchNotifications`
- `useEffect` ראשון (mount fetch)
- `useEffect` על `linkup-notifications-refresh`

### מה נשאר ללא שינוי

- `[useChatNotificationsFeed.ts](frontend/src/context/useChatNotificationsFeed.ts)`
- `[useChatNotificationsWebSocket.ts](frontend/src/context/useChatNotificationsWebSocket.ts)` (אופציונלי: אחרי A אפשר להסיר את `dispatchEvent('linkup-notifications-refresh')` אם אין עוד מאזינים — לוודא ב־`grep` לפני מחיקה)
- לוגיקת `markNotificationRead` / `useEffect` שמסמן פריטים — נשארת ב־`useNotifications` (או מועברת אם תרצו בהמשך)
- `[Notifications.tsx](frontend/src/pages/Notifications.tsx)` — כנראה ללא שינוי API אם `useNotifications` ממשיך להחזיר אותם שמות (`list`, `grouped`, …)

## למה A ולא B

B פותרת רק את ה־GET הכפול בשורה 31 אבל משאירה שני עותקים של הרשימה (context + state מקומי). A — רשימה אחת, polling/WS נשארים במקום אחד.

---

## הערות קריטיות ליישום (לא להעתיק בלי תיקון)

הדוגמה שהוצעה משתמשת ב־`const loading = list.length === 0` — **שגוי למוצר**: רשימה ריקה היא מצב תקין ("אין התראות"), לא טעינה.

**כיוונים לתקן:**

1. **אפשרות מומלצת:** להוסיף ב־context (או ב־feed hook) דגלים `notificationsLoading` / `notificationsError` שמעודכנים סביב `refreshUnreadNotifications` (לפני/אחרי fetch, ו־catch), ולחשוף אותם ב־`ChatContextValue`. אז `useNotifications` רק מעביר אותם למסך.
2. **אלטרנטיבה:** `loading = userId && !notificationsHydrated` — למשל אחרי `SET_NOTIFICATION_STATE` הראשון אחרי login להפוך `hydrated` ל־true (דורש action או ref ב־provider).

**שגיאות רשת:** היום ה־context ב־catch מציג רשימה ריקה בלי הודעת משתמש. אם רוצים לשמור את `ErrorBanner` במסך, חובה `notificationsError` (או שקול) מה־context.

---

## אחרי היישום

- `npm run build`, `npm test`, `npm run lint`
- `grep linkup-notifications-refresh` — לוודא שאין מאזינים יתומים או לנקות את האירוע אם כבר מיותר

