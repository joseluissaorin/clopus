---
name: flutter-mobile
description: Flutter mobile app development
version: 1.0.0
category: development
technologies: [flutter, dart, firebase]
triggers:
  - flutter
  - dart
  - flutter app
  - cross-platform mobile
---

# Flutter Mobile Development

Cross-platform mobile app development with Flutter.

## Capabilities

- iOS and Android development
- State management (Riverpod, Bloc)
- Navigation (go_router)
- Firebase integration
- REST API integration
- Local storage
- Push notifications
- App store deployment

## Project Structure

```
project/
├── lib/
│   ├── main.dart
│   ├── app.dart
│   ├── core/
│   │   ├── constants/
│   │   ├── theme/
│   │   └── utils/
│   ├── features/
│   │   └── {feature}/
│   │       ├── data/
│   │       ├── domain/
│   │       └── presentation/
│   └── shared/
│       └── widgets/
├── test/
├── android/
├── ios/
└── pubspec.yaml
```

## Setup

```bash
# Create project
flutter create --org com.example my_app

# Add dependencies
flutter pub add riverpod
flutter pub add go_router
flutter pub add dio
flutter pub add freezed_annotation
flutter pub add json_annotation

# Dev dependencies
flutter pub add -d build_runner
flutter pub add -d freezed
flutter pub add -d json_serializable

# Generate code
flutter pub run build_runner build
```

## Widget Pattern

```dart
class MyWidget extends ConsumerWidget {
  const MyWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(myProvider);

    return state.when(
      loading: () => const CircularProgressIndicator(),
      error: (err, stack) => Text('Error: $err'),
      data: (data) => ListView.builder(
        itemCount: data.length,
        itemBuilder: (context, index) => ListTile(
          title: Text(data[index].title),
        ),
      ),
    );
  }
}
```

## Best Practices

1. Use Riverpod for state management
2. Follow feature-first architecture
3. Use freezed for immutable models
4. Implement proper error handling
5. Write widget tests
6. Use const constructors
7. Handle platform differences
