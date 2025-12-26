---
name: expo-mobile
description: Build cross-platform mobile apps with Expo and React Native
version: 1.0.0
author: CLOPUS
tools:
  - Bash
  - Edit
  - Write
  - Read
  - Glob
triggers:
  - expo
  - react native
  - mobile app
  - ios
  - android
  - cross-platform mobile
---

# Expo Mobile Development

## Context

You are an expert mobile developer building cross-platform apps using:
- Expo SDK 50+
- React Native
- TypeScript
- Expo Router for navigation
- NativeWind (Tailwind for RN)

## Project Structure

```
├── app/                    # Expo Router pages
│   ├── _layout.tsx         # Root layout
│   ├── index.tsx           # Home screen
│   ├── (tabs)/             # Tab navigation
│   │   ├── _layout.tsx
│   │   ├── home.tsx
│   │   └── profile.tsx
│   └── [id].tsx            # Dynamic route
├── components/
│   ├── ui/                 # Reusable components
│   └── screens/            # Screen-specific components
├── hooks/                  # Custom hooks
├── lib/                    # Utilities
├── constants/              # App constants
├── assets/                 # Images, fonts
└── app.json               # Expo config
```

## Instructions

### 1. Project Initialization

```bash
npx create-expo-app@latest my-app -t tabs
cd my-app
npx expo install expo-router
```

### 2. Expo Router Navigation

```tsx
// app/_layout.tsx
import { Stack } from 'expo-router'

export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: 'Home' }} />
      <Stack.Screen name="details" options={{ title: 'Details' }} />
    </Stack>
  )
}
```

### 3. Tab Navigation

```tsx
// app/(tabs)/_layout.tsx
import { Tabs } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'

export default function TabLayout() {
  return (
    <Tabs>
      <Tabs.Screen
        name="home"
        options={{
          title: 'Home',
          tabBarIcon: ({ color }) => (
            <Ionicons name="home" size={24} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color }) => (
            <Ionicons name="person" size={24} color={color} />
          ),
        }}
      />
    </Tabs>
  )
}
```

### 4. Screen Components

```tsx
// app/(tabs)/home.tsx
import { View, Text, FlatList, Pressable } from 'react-native'
import { Link } from 'expo-router'

export default function HomeScreen() {
  const items = [{ id: '1', title: 'Item 1' }]

  return (
    <View className="flex-1 bg-white p-4">
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <Link href={`/details/${item.id}`} asChild>
            <Pressable className="p-4 border-b border-gray-200">
              <Text className="text-lg">{item.title}</Text>
            </Pressable>
          </Link>
        )}
      />
    </View>
  )
}
```

### 5. API Integration

```tsx
// hooks/useApi.ts
import { useQuery, useMutation } from '@tanstack/react-query'

export function useItems() {
  return useQuery({
    queryKey: ['items'],
    queryFn: async () => {
      const res = await fetch('https://api.example.com/items')
      return res.json()
    },
  })
}
```

### 6. State Management with Zustand

```tsx
// lib/store.ts
import { create } from 'zustand'

interface AuthState {
  user: User | null
  setUser: (user: User | null) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}))
```

### 7. Native Features

```tsx
// Using camera
import { Camera } from 'expo-camera'

// Using location
import * as Location from 'expo-location'

// Using notifications
import * as Notifications from 'expo-notifications'

// Using secure storage
import * as SecureStore from 'expo-secure-store'
```

## Best Practices

1. **Use Expo Router** - File-based navigation
2. **TypeScript everywhere** - Type safety
3. **NativeWind for styling** - Tailwind syntax
4. **React Query for data** - Caching and sync
5. **Zustand for state** - Simple global state
6. **Expo SDK modules** - Native features
7. **EAS Build** - Cloud builds for stores

## Common Packages

```bash
# Essential
npx expo install expo-router expo-linking expo-constants

# UI
npx expo install nativewind tailwindcss

# Data
npm install @tanstack/react-query zustand

# Auth
npx expo install expo-auth-session expo-web-browser expo-secure-store

# Native features
npx expo install expo-camera expo-location expo-notifications expo-image-picker
```

## Build & Deploy

```bash
# Development
npx expo start

# Build for stores
npx eas build --platform all

# Submit to stores
npx eas submit --platform all
```

## Validation

- Test on both iOS and Android simulators
- Check responsive layouts on different screen sizes
- Verify deep linking works correctly
- Test offline functionality
- Validate native permissions handling
