import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/ui.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({required this.user, super.key});

  final AppUser user;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _api = const ApiService();
  late Future<_HomeData> _future;

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
    ]);

    return _HomeData(
      featured: _api.listFrom(results[0].body),
      muscles: _api.listFrom(results[1].body),
      tips: _api.listFrom(results[2].body),
      workouts: _api.listFrom(results[3].body),
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
                final data = snapshot.data;
                return ListView(
                  padding: const EdgeInsets.only(bottom: 24),
                  children: [
                    ScreenHeader(
                      title: 'Xin chào, ${widget.user.fullName}',
                      subtitle: widget.user.isPremium
                          ? 'Tài khoản Premium đang hoạt động.'
                          : 'Khám phá bài tập, lộ trình và mẹo luyện tập.',
                      trailing: CircleAvatar(
                        backgroundColor: AppColors.accentPurple,
                        child: Text(widget.user.fullName.characters.first
                            .toUpperCase()),
                      ),
                    ),
                    if (snapshot.connectionState == ConnectionState.waiting)
                      const Center(
                          child: Padding(
                              padding: EdgeInsets.all(32),
                              child: CircularProgressIndicator()))
                    else if (snapshot.hasError)
                      const _ErrorCard()
                    else ...[
                      _HeroCard(featured: data?.featured ?? const []),
                      _Section(
                          title: 'Nhóm cơ',
                          items: data?.muscles ?? const [],
                          icon: Icons.accessibility_new),
                      _Section(
                          title: 'Mẹo luyện tập',
                          items: data?.tips ?? const [],
                          icon: Icons.tips_and_updates_outlined),
                      _WorkoutSection(items: data?.workouts ?? const []),
                    ],
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

class _HomeData {
  const _HomeData({
    required this.featured,
    required this.muscles,
    required this.tips,
    required this.workouts,
  });

  final List<Map<String, dynamic>> featured;
  final List<Map<String, dynamic>> muscles;
  final List<Map<String, dynamic>> tips;
  final List<Map<String, dynamic>> workouts;
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({required this.featured});

  final List<Map<String, dynamic>> featured;

  @override
  Widget build(BuildContext context) {
    final first = featured.isNotEmpty ? featured.first : <String, dynamic>{};
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.bolt, color: AppColors.accentYellow, size: 34),
            const SizedBox(height: 12),
            Text(
              (first['title'] ?? 'Luyện tập thông minh hơn').toString(),
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            Text(
              (first['desc'] ??
                      first['description'] ??
                      'FIT ME giúp bạn theo dõi bài tập, hồ sơ và tiến độ trong một ứng dụng mobile.')
                  .toString(),
              style: const TextStyle(color: AppColors.textMuted, height: 1.45),
            ),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    required this.items,
    required this.icon,
  });

  final String title;
  final List<Map<String, dynamic>> items;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style:
                  const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),
          ...items.take(4).map((item) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: AppCard(
                child: Row(
                  children: [
                    Icon(icon, color: AppColors.accentYellow),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                              (item['title'] ?? item['name'] ?? 'Nội dung')
                                  .toString(),
                              style:
                                  const TextStyle(fontWeight: FontWeight.w800)),
                          const SizedBox(height: 4),
                          Text(
                            (item['content'] ??
                                    item['desc'] ??
                                    item['description'] ??
                                    '')
                                .toString(),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                color: AppColors.textMuted, fontSize: 13),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _WorkoutSection extends StatelessWidget {
  const _WorkoutSection({required this.items});

  final List<Map<String, dynamic>> items;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Lịch tập mẫu',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          const SizedBox(height: 10),
          ...items.take(5).map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: AppCard(
                  child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.calendar_month,
                        color: AppColors.accentPurple),
                    title: Text((item['title'] ?? 'Ngày tập').toString()),
                    subtitle: Text(
                        (item['category'] ?? item['focus'] ?? '').toString()),
                  ),
                ),
              )),
        ],
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(20),
      child: AppCard(
        child: Text(
          'Không tải được dữ liệu. Hãy kiểm tra backend Flask.',
          style: TextStyle(color: AppColors.textMuted),
        ),
      ),
    );
  }
}
