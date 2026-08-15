import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/ui.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    required this.user,
    required this.onOpenExercises,
    required this.onOpenPlan,
    required this.onOpenCoach,
    super.key,
  });

  final AppUser user;
  final VoidCallback onOpenExercises;
  final VoidCallback onOpenPlan;
  final VoidCallback onOpenCoach;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _api = const ApiService();
  late Future<_HomeData> _future;
  String _planTab = 'split';

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_HomeData> _load() async {
    final results = await Future.wait([
      _api.get('/api/featured'),
      _api.get('/api/muscles-info'),
      _api.get('/api/tips'),
      _api.get('/api/sample-workouts'),
      _api.get('/api/hero-stats'),
    ]);

    return _HomeData(
      featured: _api.listFrom(results[0].body),
      muscles: _api.listFrom(results[1].body),
      tips: _api.listFrom(results[2].body),
      workouts: _api.listFrom(results[3].body),
      stats: _api.listFrom(results[4].body),
    );
  }

  Future<void> _refresh() async {
    setState(() => _future = _load());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        const Positioned.fill(child: GridBackground()),
        SafeArea(
          child: RefreshIndicator(
            onRefresh: _refresh,
            child: FutureBuilder<_HomeData>(
              future: _future,
              builder: (context, snapshot) {
                final data = snapshot.data ?? _HomeData.empty();
                if (snapshot.connectionState == ConnectionState.waiting &&
                    snapshot.data == null) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError && snapshot.data == null) {
                  return _ErrorState(onRetry: () {
                    setState(() => _future = _load());
                  });
                }

                return ListView(
                  padding: const EdgeInsets.fromLTRB(20, 18, 20, 28),
                  children: [
                    _HomeHero(
                      user: widget.user,
                      stats: data.stats,
                      onOpenExercises: widget.onOpenExercises,
                      onOpenPlan: widget.onOpenPlan,
                      onOpenCoach: widget.onOpenCoach,
                    ),
                    const SizedBox(height: 14),
                    _ShortcutGrid(
                      onOpenExercises: widget.onOpenExercises,
                      onOpenPlan: widget.onOpenPlan,
                      onOpenCoach: widget.onOpenCoach,
                    ),
                    const SizedBox(height: 18),
                    _FeaturedSection(items: data.featured),
                    const SizedBox(height: 18),
                    _MuscleSection(
                      items: data.muscles,
                      onOpenExercises: widget.onOpenExercises,
                    ),
                    const SizedBox(height: 18),
                    _TipsSection(items: data.tips),
                    const SizedBox(height: 18),
                    _WorkoutPlanSection(
                      items: data.workouts,
                      selected: _planTab,
                      onSelected: (value) => setState(() => _planTab = value),
                      onOpenPlan: widget.onOpenPlan,
                    ),
                  ],
                );
              },
            ),
          ),
        ),
      ],
    );
  }
}

class _HomeHero extends StatelessWidget {
  const _HomeHero({
    required this.user,
    required this.stats,
    required this.onOpenExercises,
    required this.onOpenPlan,
    required this.onOpenCoach,
  });

  final AppUser user;
  final List<Map<String, dynamic>> stats;
  final VoidCallback onOpenExercises;
  final VoidCallback onOpenPlan;
  final VoidCallback onOpenCoach;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.accentYellow.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: AppColors.accentYellow.withValues(alpha: 0.25),
                  ),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.bolt, size: 15, color: AppColors.accentYellow),
                    SizedBox(width: 6),
                    Text(
                      'FIT ME MOBILE',
                      style: TextStyle(
                        color: AppColors.accentYellow,
                        fontSize: 12,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              CircleAvatar(
                radius: 19,
                backgroundColor: AppColors.accentPurple,
                child: Text(
                  _initial(user.fullName),
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Rèn luyện\nkhông ngừng',
            style: const TextStyle(
              fontSize: 34,
              height: 0.98,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Xin chào, ${user.fullName}. Khám phá bài tập, tạo lộ trình cá nhân hóa và theo dõi tiến độ trong một ứng dụng.',
            style: const TextStyle(
              color: AppColors.textMuted,
              height: 1.45,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: onOpenPlan,
                  icon: const Icon(Icons.route_outlined, size: 18),
                  label: const Text('Bắt đầu'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onOpenExercises,
                  icon: const Icon(Icons.fitness_center, size: 18),
                  label: const Text('Khám phá'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: onOpenCoach,
              icon: const Icon(Icons.smart_toy_outlined, size: 18),
              label: const Text('Hỏi AI Coach'),
            ),
          ),
          if (stats.isNotEmpty) ...[
            const SizedBox(height: 14),
            _HeroStats(items: stats),
          ],
        ],
      ),
    );
  }
}

class _HeroStats extends StatelessWidget {
  const _HeroStats({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    final visible = items.take(3).toList();
    return Row(
      children: [
        for (var i = 0; i < visible.length; i++) ...[
          if (i > 0) const SizedBox(width: 10),
          Expanded(
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.bgInput,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  FittedBox(
                    alignment: Alignment.centerLeft,
                    fit: BoxFit.scaleDown,
                    child: Text(
                      _text(visible[i]['number_text'], fallback: '--'),
                      style: const TextStyle(
                        color: AppColors.accentYellow,
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _text(visible[i]['label_text'], fallback: 'Thống kê'),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 11,
                      height: 1.2,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _ShortcutGrid extends StatelessWidget {
  const _ShortcutGrid({
    required this.onOpenExercises,
    required this.onOpenPlan,
    required this.onOpenCoach,
  });

  final VoidCallback onOpenExercises;
  final VoidCallback onOpenPlan;
  final VoidCallback onOpenCoach;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _ShortcutCard(
            icon: Icons.fitness_center,
            title: 'Thư viện',
            subtitle: 'Bài tập theo nhóm cơ',
            color: AppColors.accentPurple,
            onTap: onOpenExercises,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _ShortcutCard(
            icon: Icons.route,
            title: 'Lộ trình',
            subtitle: 'AI cá nhân hóa',
            color: AppColors.accentYellow,
            onTap: onOpenPlan,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _ShortcutCard(
            icon: Icons.smart_toy_outlined,
            title: 'AI Coach',
            subtitle: 'Tư vấn nhanh',
            color: AppColors.success,
            onTap: onOpenCoach,
          ),
        ),
      ],
    );
  }
}

class _ShortcutCard extends StatelessWidget {
  const _ShortcutCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(12),
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(height: 10),
          Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 3),
          Text(
            subtitle,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppColors.textMuted,
              fontSize: 11,
              height: 1.25,
            ),
          ),
        ],
      ),
    );
  }
}

class _FeaturedSection extends StatelessWidget {
  const _FeaturedSection({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    return _SectionBlock(
      label: 'Khám phá',
      title: 'Nội dung nổi bật',
      child: items.isEmpty
          ? const _EmptyBox(text: 'Chưa có nội dung nổi bật.')
          : SizedBox(
              height: 188,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: items.take(6).length,
                separatorBuilder: (_, __) => const SizedBox(width: 10),
                itemBuilder: (context, index) {
                  final item = items[index];
                  return SizedBox(
                    width: 248,
                    child: AppCard(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                _text(item['icon'], fallback: '•'),
                                style: const TextStyle(fontSize: 26),
                              ),
                              const Spacer(),
                              _MiniTag(
                                  _text(item['tag'], fallback: 'Kiến thức')),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _text(item['title'], fallback: 'Nội dung'),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 17,
                              height: 1.15,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            child: Text(
                              _text(
                                item['description'] ?? item['desc'],
                                fallback: '',
                              ),
                              maxLines: 4,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: AppColors.textMuted,
                                fontSize: 12,
                                height: 1.35,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
    );
  }
}

class _MuscleSection extends StatelessWidget {
  const _MuscleSection({
    required this.items,
    required this.onOpenExercises,
  });

  final List<Map<String, dynamic>> items;
  final VoidCallback onOpenExercises;

  @override
  Widget build(BuildContext context) {
    return _SectionBlock(
      label: 'Thư viện',
      title: 'Nhóm cơ & bài tập',
      trailing: TextButton.icon(
        onPressed: onOpenExercises,
        icon: const Icon(Icons.arrow_forward, size: 17),
        label: const Text('Mở'),
      ),
      child: items.isEmpty
          ? const _EmptyBox(text: 'Chưa có dữ liệu nhóm cơ.')
          : GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: items.take(8).length,
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                childAspectRatio: 1.8,
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
              ),
              itemBuilder: (context, index) {
                final item = items[index];
                return AppCard(
                  padding: const EdgeInsets.all(12),
                  onTap: onOpenExercises,
                  child: Row(
                    children: [
                      Text(
                        _text(item['icon'], fallback: '•'),
                        style: const TextStyle(fontSize: 24),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              _text(item['name'], fallback: 'Nhóm cơ'),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style:
                                  const TextStyle(fontWeight: FontWeight.w900),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              _text(
                                item['exercise_count'],
                                fallback: '0 bài tập',
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: AppColors.textMuted,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}

class _TipsSection extends StatelessWidget {
  const _TipsSection({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    return _SectionBlock(
      label: 'Kiến thức',
      title: 'Mẹo tập luyện',
      child: items.isEmpty
          ? const _EmptyBox(text: 'Chưa có mẹo tập luyện.')
          : Column(
              children: [
                for (var i = 0; i < items.take(4).length; i++)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: AppCard(
                      padding: const EdgeInsets.all(14),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SizedBox(
                            width: 42,
                            child: Text(
                              '0${i + 1}',
                              style: const TextStyle(
                                color: AppColors.border,
                                fontSize: 28,
                                height: 1,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _text(items[i]['title'], fallback: 'Mẹo tập'),
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                                const SizedBox(height: 5),
                                Text(
                                  _text(items[i]['content'], fallback: ''),
                                  maxLines: 3,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: AppColors.textMuted,
                                    fontSize: 12,
                                    height: 1.35,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
    );
  }
}

class _WorkoutPlanSection extends StatelessWidget {
  const _WorkoutPlanSection({
    required this.items,
    required this.selected,
    required this.onSelected,
    required this.onOpenPlan,
  });

  final List<Map<String, dynamic>> items;
  final String selected;
  final ValueChanged<String> onSelected;
  final VoidCallback onOpenPlan;

  @override
  Widget build(BuildContext context) {
    final filtered = items
        .where((item) => _text(item['category'], fallback: 'split') == selected)
        .toList();
    final shown =
        filtered.isEmpty ? items.take(4).toList() : filtered.take(6).toList();

    return _SectionBlock(
      label: 'Lộ trình',
      title: 'Lịch tập mẫu',
      trailing: TextButton.icon(
        onPressed: onOpenPlan,
        icon: const Icon(Icons.auto_awesome, size: 17),
        label: const Text('Tạo AI'),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'split', label: Text('PPL')),
              ButtonSegment(value: 'fullbody', label: Text('Full')),
              ButtonSegment(value: 'upperlower', label: Text('Upper')),
            ],
            selected: {selected},
            onSelectionChanged: (value) => onSelected(value.first),
          ),
          const SizedBox(height: 12),
          if (shown.isEmpty)
            const _EmptyBox(text: 'Chưa có lịch tập mẫu.')
          else
            ...shown.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: AppCard(
                  padding: const EdgeInsets.all(14),
                  onTap: onOpenPlan,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          _MiniTag(_text(item['day_label'], fallback: 'Ngày')),
                          const Spacer(),
                          if (item['is_rest_day'] == true)
                            const Icon(
                              Icons.hotel_outlined,
                              color: AppColors.textMuted,
                              size: 18,
                            )
                          else
                            const Icon(
                              Icons.fitness_center,
                              color: AppColors.accentYellow,
                              size: 18,
                            ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        _text(item['title'], fallback: 'Ngày tập'),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      ..._mapsFrom(item['exercises']).take(3).map(
                            (ex) => Padding(
                              padding: const EdgeInsets.only(bottom: 5),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.check,
                                    size: 14,
                                    color: AppColors.success,
                                  ),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      _text(ex['name'], fallback: 'Bài tập'),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(fontSize: 12),
                                    ),
                                  ),
                                  if (_text(ex['sets_reps']).isNotEmpty)
                                    Text(
                                      _text(ex['sets_reps']),
                                      style: const TextStyle(
                                        color: AppColors.textMuted,
                                        fontSize: 11,
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _SectionBlock extends StatelessWidget {
  const _SectionBlock({
    required this.label,
    required this.title,
    required this.child,
    this.trailing,
  });

  final String label;
  final String title;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label.toUpperCase(),
                    style: const TextStyle(
                      color: AppColors.accentYellow,
                      fontSize: 11,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
            ),
            if (trailing != null) trailing!,
          ],
        ),
        const SizedBox(height: 10),
        child,
      ],
    );
  }
}

class _MiniTag extends StatelessWidget {
  const _MiniTag(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: AppColors.accentPurple.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: AppColors.accentPurple.withValues(alpha: 0.28),
        ),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          color: AppColors.accentYellow,
          fontSize: 10,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _EmptyBox extends StatelessWidget {
  const _EmptyBox({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(14),
      child: Text(text, style: const TextStyle(color: AppColors.textMuted)),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: AppCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_outlined, color: AppColors.danger),
              const SizedBox(height: 10),
              const Text(
                'Không tải được dữ liệu trang chủ.',
                style: TextStyle(fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 12),
              PrimaryButton(label: 'Thử lại', onPressed: onRetry),
            ],
          ),
        ),
      ),
    );
  }
}

class _HomeData {
  const _HomeData({
    required this.featured,
    required this.muscles,
    required this.tips,
    required this.workouts,
    required this.stats,
  });

  factory _HomeData.empty() => const _HomeData(
        featured: [],
        muscles: [],
        tips: [],
        workouts: [],
        stats: [],
      );

  final List<Map<String, dynamic>> featured;
  final List<Map<String, dynamic>> muscles;
  final List<Map<String, dynamic>> tips;
  final List<Map<String, dynamic>> workouts;
  final List<Map<String, dynamic>> stats;
}

List<Map<String, dynamic>> _mapsFrom(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }
  return const [];
}

String _text(dynamic value, {String fallback = ''}) {
  final text = value?.toString().trim() ?? '';
  return text.isEmpty || text == 'null' ? fallback : text;
}

String _initial(String value) {
  final trimmed = value.trim();
  return trimmed.isEmpty ? 'F' : trimmed[0].toUpperCase();
}
