# Frontend Patterns for PointCV

## Next.js 14 App Router
- Server Components by default
- 'use client' ONLY for:
  - Interactivity (buttons, forms)
  - Browser APIs (localStorage, EventSource)
  - Hooks (useState, useEffect)
  - Clerk components (UserButton, SignIn)

## Data Fetching
```typescript
// Server Component
const orders = await api.getOrders(); // Direct fetch

// Client Component
useEffect(() => {
  api.getOrders().then(setOrders);
}, []);
```

## API Client Pattern
```typescript
// lib/api.ts
const api = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_URL });

api.interceptors.request.use(async (config) => {
  const token = await window.Clerk?.session?.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```

## Form Pattern
```typescript
const form = useForm<FormData>({
  resolver: zodResolver(schema),
  defaultValues: {...}
});
```

## Bilingual Pattern
```typescript
// lib/i18n/useTranslation.ts
const { t, lang } = useTranslation();
// t('hero.title') -> looks up id.json or en.json
```
