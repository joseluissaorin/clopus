# Expo App Template

A production-ready cross-platform mobile app built with Expo and React Native.

## Features

- **Expo Router** - File-based navigation
- **TypeScript** - Type safety
- **NativeWind** - Tailwind CSS for React Native
- **Authentication** - Secure login/logout
- **Push Notifications** - Expo Notifications
- **Offline Support** - React Query persistence
- **Dark Mode** - System + manual toggle
- **Secure Storage** - Encrypted credential storage

## Project Structure

```
{{PROJECT_NAME}}/
├── app/                        # Expo Router pages
│   ├── _layout.tsx             # Root layout
│   ├── index.tsx               # Home screen
│   ├── (auth)/                 # Auth screens
│   │   ├── _layout.tsx
│   │   ├── login.tsx
│   │   └── register.tsx
│   ├── (tabs)/                 # Tab navigation
│   │   ├── _layout.tsx
│   │   ├── home.tsx
│   │   ├── explore.tsx
│   │   └── profile.tsx
│   └── [id].tsx                # Dynamic route
├── components/
│   ├── ui/                     # Reusable components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Card.tsx
│   │   └── Avatar.tsx
│   └── screens/                # Screen-specific components
├── hooks/
│   ├── useAuth.ts
│   ├── useTheme.ts
│   └── useNotifications.ts
├── lib/
│   ├── api.ts                  # API client
│   ├── storage.ts              # Secure storage
│   └── utils.ts
├── store/
│   └── index.ts                # Zustand store
├── constants/
│   ├── colors.ts
│   └── config.ts
├── assets/
│   ├── images/
│   └── fonts/
├── app.json                    # Expo config
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── babel.config.js
```

## Setup

```bash
# Create project
npx create-expo-app@latest {{PROJECT_NAME}} -t tabs
cd {{PROJECT_NAME}}

# Install dependencies
npx expo install expo-router expo-linking expo-constants expo-status-bar
npx expo install expo-secure-store expo-notifications
npm install nativewind tailwindcss @tanstack/react-query zustand

# Configure NativeWind
npx tailwindcss init
```

## Configuration

### app.json

```json
{
  "expo": {
    "name": "{{PROJECT_NAME}}",
    "slug": "{{PROJECT_NAME}}",
    "version": "1.0.0",
    "orientation": "portrait",
    "icon": "./assets/images/icon.png",
    "scheme": "{{PROJECT_NAME}}",
    "userInterfaceStyle": "automatic",
    "ios": {
      "bundleIdentifier": "{{BUNDLE_ID}}",
      "supportsTablet": true
    },
    "android": {
      "package": "{{BUNDLE_ID}}",
      "adaptiveIcon": {
        "foregroundImage": "./assets/images/adaptive-icon.png",
        "backgroundColor": "#ffffff"
      }
    },
    "plugins": [
      "expo-router",
      "expo-secure-store"
    ]
  }
}
```

### API Client

```typescript
// lib/api.ts
import * as SecureStore from 'expo-secure-store';

const API_URL = '{{API_URL}}';

async function getToken() {
  return await SecureStore.getItemAsync('auth_token');
}

export const api = {
  get: async <T>(path: string): Promise<T> => {
    const token = await getToken();
    const res = await fetch(`${API_URL}${path}`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
    });
    return res.json();
  },

  post: async <T>(path: string, data: unknown): Promise<T> => {
    const token = await getToken();
    const res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
      },
      body: JSON.stringify(data),
    });
    return res.json();
  },
};
```

### Authentication

```typescript
// hooks/useAuth.ts
import * as SecureStore from 'expo-secure-store';
import { create } from 'zustand';
import { api } from '../lib/api';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  login: async (email, password) => {
    const { user, token } = await api.post('/auth/login', { email, password });
    await SecureStore.setItemAsync('auth_token', token);
    set({ user });
  },

  logout: async () => {
    await SecureStore.deleteItemAsync('auth_token');
    set({ user: null });
  },

  checkAuth: async () => {
    try {
      const token = await SecureStore.getItemAsync('auth_token');
      if (token) {
        const user = await api.get('/auth/me');
        set({ user, isLoading: false });
      } else {
        set({ isLoading: false });
      }
    } catch {
      set({ isLoading: false });
    }
  },
}));
```

## Components

### Button Component

```tsx
// components/ui/Button.tsx
import { Pressable, Text, ActivityIndicator } from 'react-native';
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'flex-row items-center justify-center rounded-lg',
  {
    variants: {
      variant: {
        primary: 'bg-blue-600 active:bg-blue-700',
        secondary: 'bg-gray-200 active:bg-gray-300',
        outline: 'border border-gray-300',
      },
      size: {
        sm: 'px-3 py-2',
        md: 'px-4 py-3',
        lg: 'px-6 py-4',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

interface ButtonProps extends VariantProps<typeof buttonVariants> {
  onPress: () => void;
  children: string;
  loading?: boolean;
  disabled?: boolean;
}

export function Button({ onPress, children, loading, disabled, variant, size }: ButtonProps) {
  return (
    <Pressable
      onPress={onPress}
      disabled={loading || disabled}
      className={buttonVariants({ variant, size })}
    >
      {loading ? (
        <ActivityIndicator color="white" />
      ) : (
        <Text className="text-white font-semibold">{children}</Text>
      )}
    </Pressable>
  );
}
```

## Development

```bash
# Start development
npx expo start

# Run on iOS simulator
npx expo run:ios

# Run on Android emulator
npx expo run:android
```

## Building

```bash
# Configure EAS
npx eas init

# Build for development
npx eas build --platform all --profile development

# Build for app stores
npx eas build --platform all --profile production

# Submit to stores
npx eas submit --platform all
```
