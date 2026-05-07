export const qk = {
  auth: {
    me: () => ['auth', 'me'] as const,
  },
  billing: {
    status: () => ['billing', 'status'] as const,
  },
  rides: {
    list: (filters?: Record<string, unknown>) => ['rides', 'list', filters] as const,
    detail: (id: string) => ['rides', id] as const,
  },
  bookings: {
    driver: (userId?: string) => ['bookings', 'driver', userId] as const,
    driverActive: (userId?: string) => ['bookings', 'driver', 'active', userId] as const,
    driverHistory: (userId?: string) => ['bookings', 'driver', 'history', userId] as const,
    passenger: (userId?: string) => ['bookings', 'passenger', userId] as const,
    passengerActive: (userId?: string) => ['bookings', 'passenger', 'active', userId] as const,
    passengerHistory: (userId?: string) => ['bookings', 'passenger', 'history', userId] as const,
  },
  groups: {
    list: () => ['groups', 'list'] as const,
    detail: (id: string) => ['groups', id] as const,
    members: (id: string) => ['groups', id, 'members'] as const,
    rides: (id: string) => ['groups', id, 'rides'] as const,
  },
  chat: {
    conversations: (limit: number = 30) => ['chat', 'conversations', 'list', limit] as const,
    conversation: (id: string) => ['chat', 'conversations', id] as const,
    messages: (id: string) => ['chat', 'messages', id] as const,
    unread: () => ['chat', 'unread'] as const,
  },
  notifications: {
    all: () => ['notifications'] as const,
    page: (limit: number = 20) => ['notifications', 'page', limit] as const,
  },
  passengers: {
    requests: () => ['passengers', 'requests'] as const,
  },
  presence: {
    partner: (id: string) => ['presence', id] as const,
  },
  geo: {
    mapsKey: () => ['geo', 'mapsKey'] as const,
  },
  admin: {
    stats: () => ['admin', 'stats'] as const,
    users: (filters?: Record<string, unknown>) => ['admin', 'users', filters] as const,
    rides: (filters?: Record<string, unknown>) => ['admin', 'rides', filters] as const,
    groups: (filters?: Record<string, unknown>) => ['admin', 'groups', filters] as const,
    outbox: (filters?: Record<string, unknown>) => ['admin', 'outbox', filters] as const,
    bookings: (filters?: Record<string, unknown>) => ['admin', 'bookings', filters] as const,
    billing: (filters?: Record<string, unknown>) => ['admin', 'billing', filters] as const,
    audit: (filters?: Record<string, unknown>) => ['admin', 'audit', filters] as const,
    opsOverview: () => ['admin', 'ops', 'overview'] as const,
    queues: () => ['admin', 'queues'] as const,
    workers: () => ['admin', 'workers'] as const,
    health: () => ['admin', 'health'] as const,
  },
} as const;

export const mk = {
  billing: {
    checkout: () => ['billing', 'checkout'] as const,
  },
  auth: {
    login: () => ['auth', 'login'] as const,
    register: () => ['auth', 'register'] as const,
    logout: () => ['auth', 'logout'] as const,
    refresh: () => ['auth', 'refresh'] as const,
  },
  rides: {
    create: () => ['rides', 'create'] as const,
    cancel: (id: string) => ['rides', id, 'cancel'] as const,
    update: (id: string) => ['rides', id, 'update'] as const,
  },
  bookings: {
    approve: (id: string) => ['bookings', id, 'approve'] as const,
    reject: (id: string) => ['bookings', id, 'reject'] as const,
    cancel: (id: string) => ['bookings', id, 'cancel'] as const,
  },
  groups: {
    create: () => ['groups', 'create'] as const,
    join: () => ['groups', 'join'] as const,
    leave: (id: string) => ['groups', id, 'leave'] as const,
  },
  chat: {
    send: (conversationId: string) => ['chat', 'send', conversationId] as const,
    markRead: (conversationId: string) => ['chat', 'markRead', conversationId] as const,
  },
  uploads: {
    avatarConfirm: () => ['uploads', 'avatarConfirm'] as const,
  },
} as const;
