import 'package:flutter/material.dart';

import '../core/api_service.dart';
import '../core/app_colors.dart';

String resolveExerciseImageUrl(dynamic raw) {
  final value = (raw ?? '').toString().trim().replaceAll('\\', '/');
  if (value.isEmpty || value == 'null') return '';
  final lower = value.toLowerCase();
  if (lower.startsWith('http://') ||
      lower.startsWith('https://') ||
      lower.startsWith('data:')) {
    return value;
  }
  if (value.startsWith('/api/')) return '${ApiConfig.baseUrl}$value';
  if (value.startsWith('api/')) return '${ApiConfig.baseUrl}/$value';
  if (lower.contains('images/flat/') ||
      lower.contains('image/flat/') ||
      lower.endsWith('.webp')) {
    final filename = value.split('/').where((part) => part.isNotEmpty).last;
    return '${ApiConfig.baseUrl}/api/ml/exercise-image/${Uri.encodeComponent(filename)}';
  }
  return '${ApiConfig.baseUrl}${value.startsWith('/') ? value : '/$value'}';
}

List<ExerciseImageItem> exerciseImagesFrom(Map<String, dynamic> exercise) {
  final rawImages = exercise['images'];
  final items = <ExerciseImageItem>[];
  if (rawImages is List) {
    for (var i = 0; i < rawImages.length; i++) {
      final raw = rawImages[i];
      final label = i == 0 ? 'Tư thế bắt đầu' : 'Tư thế chính';
      if (raw is Map) {
        final url = resolveExerciseImageUrl(
          raw['url'] ?? raw['path'] ?? raw['filename'] ?? raw['image'],
        );
        if (url.isNotEmpty) {
          items.add(ExerciseImageItem(
            label: (raw['label'] ?? label).toString(),
            url: url,
          ));
        }
      } else {
        final url = resolveExerciseImageUrl(raw);
        if (url.isNotEmpty) {
          items.add(ExerciseImageItem(label: label, url: url));
        }
      }
    }
  }

  if (items.isEmpty) {
    final url = resolveExerciseImageUrl(exercise['image']);
    if (url.isNotEmpty) {
      items.add(const ExerciseImageItem(label: 'Minh họa', url: '')
          .copyWith(url: url));
    }
  }
  return items;
}

class ExerciseImageItem {
  const ExerciseImageItem({required this.label, required this.url});

  final String label;
  final String url;

  ExerciseImageItem copyWith({String? label, String? url}) {
    return ExerciseImageItem(
      label: label ?? this.label,
      url: url ?? this.url,
    );
  }
}

class ExerciseImageView extends StatelessWidget {
  const ExerciseImageView({
    required this.url,
    this.icon,
    this.fit = BoxFit.contain,
    this.borderRadius,
    this.overlay = false,
    this.foreground,
    super.key,
  });

  final String url;
  final String? icon;
  final BoxFit fit;
  final BorderRadius? borderRadius;
  final bool overlay;
  final Widget? foreground;

  @override
  Widget build(BuildContext context) {
    final fallback = Center(
      child: Text(
        icon?.isNotEmpty == true ? icon! : '🏋️',
        style: const TextStyle(fontSize: 42),
      ),
    );
    final child = url.isEmpty
        ? fallback
        : Image.network(
            url,
            width: double.infinity,
            height: double.infinity,
            fit: fit,
            errorBuilder: (_, __, ___) => fallback,
            loadingBuilder: (context, child, progress) {
              if (progress == null) return child;
              return const Center(
                child: SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              );
            },
          );

    return ClipRRect(
      borderRadius: borderRadius ?? BorderRadius.zero,
      child: DecoratedBox(
        decoration: const BoxDecoration(color: AppColors.bgInput),
        child: Stack(
          fit: StackFit.expand,
          children: [
            child,
            if (overlay)
              DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.black.withValues(alpha: 0.04),
                      Colors.black.withValues(alpha: 0.55),
                    ],
                  ),
                ),
              ),
            if (foreground != null) foreground!,
          ],
        ),
      ),
    );
  }
}
