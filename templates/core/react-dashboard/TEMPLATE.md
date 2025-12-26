# React Dashboard Template

A modern, feature-rich admin dashboard built with React, TypeScript, and Tailwind CSS.

## Features

- **Authentication** - Login, logout, protected routes
- **Dark Mode** - System preference + toggle
- **Data Tables** - Sorting, filtering, pagination
- **Charts** - Line, bar, pie charts with Recharts
- **User Management** - CRUD operations
- **Responsive** - Mobile-first design
- **Sidebar Navigation** - Collapsible sidebar

## Project Structure

```
{{PROJECT_NAME}}/
├── src/
│   ├── components/
│   │   ├── ui/                 # Reusable UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Table.tsx
│   │   ├── layout/             # Layout components
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Layout.tsx
│   │   └── charts/             # Chart components
│   │       ├── LineChart.tsx
│   │       ├── BarChart.tsx
│   │       └── PieChart.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx       # Main dashboard
│   │   ├── Users.tsx           # User management
│   │   ├── Analytics.tsx       # Analytics page
│   │   ├── Settings.tsx        # Settings page
│   │   └── Login.tsx           # Login page
│   ├── hooks/
│   │   ├── useAuth.ts          # Authentication hook
│   │   ├── useTheme.ts         # Theme hook
│   │   └── useApi.ts           # API hook
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   ├── auth.ts             # Auth utilities
│   │   └── utils.ts            # Helpers
│   ├── store/
│   │   └── index.ts            # Zustand store
│   ├── types/
│   │   └── index.ts            # TypeScript types
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── README.md
```

## Setup

```bash
# Create project
npm create vite@latest {{PROJECT_NAME}} -- --template react-ts
cd {{PROJECT_NAME}}

# Install dependencies
npm install react-router-dom @tanstack/react-query zustand recharts clsx tailwind-merge
npm install -D tailwindcss postcss autoprefixer @types/node

# Initialize Tailwind
npx tailwindcss init -p
```

## Configuration

### API Configuration

```typescript
// src/lib/api.ts
const API_URL = '{{API_URL}}';

export const api = {
  get: (path: string) => fetch(`${API_URL}${path}`).then(r => r.json()),
  post: (path: string, data: unknown) => fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(r => r.json()),
};
```

### Authentication

```typescript
// src/hooks/useAuth.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      login: async (email, password) => {
        const { user, token } = await api.post('/auth/login', { email, password });
        set({ user, token });
      },
      logout: () => set({ user: null, token: null }),
    }),
    { name: 'auth-storage' }
  )
);
```

## Components

### Layout

```tsx
// src/components/layout/Layout.tsx
export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### Data Table

```tsx
// src/components/ui/Table.tsx
interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  onSort?: (key: keyof T) => void;
  onRowClick?: (row: T) => void;
}

export function Table<T>({ data, columns, onSort, onRowClick }: TableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-50 dark:bg-gray-800">
            {columns.map(col => (
              <th key={col.key} onClick={() => onSort?.(col.key)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} onClick={() => onRowClick?.(row)}>
              {columns.map(col => (
                <td key={col.key}>{col.render?.(row) ?? row[col.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

## Customization

### Theme Colors

Edit `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
    },
  },
};
```

### Adding New Pages

1. Create component in `src/pages/`
2. Add route in `App.tsx`
3. Add navigation item in `Sidebar.tsx`

## Development

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Deployment

```bash
# Build
npm run build

# Deploy to Vercel
npx vercel

# Deploy to Netlify
npx netlify deploy --prod
```
