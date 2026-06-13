import 'package:flutter/material.dart';

import '../../core/api_service.dart';
import '../../core/app_colors.dart';
import '../../shared/ui.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  final _api = const ApiService();
  int _tab = 0;
  late Future<_AdminData> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_AdminData> _load() async {
    final results = await Future.wait([
      _api.get('/api/exercises/?userId=admin'),
      _api.get('/api/users/'),
      _api.get('/api/tips?admin=true'),
      _api.get('/api/featured?admin=true'),
      _api.get('/api/faq?admin=true'),
    ]);
    return _AdminData(
      exercises: _api.listFrom(results[0].body),
      users: _api.listFrom(results[1].body),
      tips: _api.listFrom(results[2].body),
      featured: _api.listFrom(results[3].body),
      faq: _api.listFrom(results[4].body),
    );
  }

  void _reload() => setState(() => _future = _load());

  Future<void> _delete(String path) async {
    final result = await _api.delete(path);
    if (!mounted) return;
    showAppSnack(
        context, result.message ?? (result.ok ? 'Đã xoá.' : 'Không xoá được.'),
        error: !result.ok);
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        const Positioned.fill(child: GridBackground()),
        SafeArea(
          child: FutureBuilder<_AdminData>(
            future: _future,
            builder: (context, snapshot) {
              final data = snapshot.data;
              return Column(
                children: [
                  const ScreenHeader(
                      title: 'Admin',
                      subtitle: 'Quản lý nhanh theo giao diện mobile.'),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: SegmentedButton<int>(
                      segments: const [
                        ButtonSegment(value: 0, label: Text('Bài tập')),
                        ButtonSegment(value: 1, label: Text('User')),
                        ButtonSegment(value: 2, label: Text('Nội dung')),
                      ],
                      selected: {_tab},
                      onSelectionChanged: (value) =>
                          setState(() => _tab = value.first),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Expanded(
                    child: RefreshIndicator(
                      onRefresh: () async => _reload(),
                      child: snapshot.connectionState == ConnectionState.waiting
                          ? const Center(child: CircularProgressIndicator())
                          : ListView(
                              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
                              children: switch (_tab) {
                                0 =>
                                  _exerciseCards(data?.exercises ?? const []),
                                1 => _userCards(data?.users ?? const []),
                                _ => _contentCards(data),
                              },
                            ),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }

  List<Widget> _exerciseCards(List<Map<String, dynamic>> items) {
    return items
        .map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: AppCard(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.fitness_center,
                      color: AppColors.accentPurple),
                  title: Text((item['name'] ?? '').toString()),
                  subtitle:
                      Text('${item['muscle'] ?? ''} • ${item['diff'] ?? ''}'),
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline,
                        color: AppColors.danger),
                    onPressed: () => _delete('/api/exercises/${item['id']}'),
                  ),
                ),
              ),
            ))
        .toList();
  }

  List<Widget> _userCards(List<Map<String, dynamic>> items) {
    return items
        .map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: AppCard(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading:
                      const Icon(Icons.person, color: AppColors.accentYellow),
                  title: Text((item['fullName'] ?? '').toString()),
                  subtitle: Text(
                      '${item['email'] ?? ''}\nRole: ${item['role'] ?? 'user'}'),
                  isThreeLine: true,
                  trailing: IconButton(
                    icon: const Icon(Icons.delete_outline,
                        color: AppColors.danger),
                    onPressed: () => _delete('/api/users/${item['id']}'),
                  ),
                ),
              ),
            ))
        .toList();
  }

  List<Widget> _contentCards(_AdminData? data) {
    final items = [
      ...?data?.featured.map((e) => {'type': 'featured', ...e}),
      ...?data?.tips.map((e) => {'type': 'tips', ...e}),
      ...?data?.faq.map((e) => {'type': 'faq', ...e}),
    ];
    return items
        .map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: AppCard(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.article_outlined,
                      color: AppColors.accentPurple),
                  title: Text(
                      (item['title'] ?? item['q'] ?? item['question'] ?? '')
                          .toString()),
                  subtitle: Text((item['type'] ?? '').toString()),
                ),
              ),
            ))
        .toList();
  }
}

class _AdminData {
  const _AdminData({
    required this.exercises,
    required this.users,
    required this.tips,
    required this.featured,
    required this.faq,
  });

  final List<Map<String, dynamic>> exercises;
  final List<Map<String, dynamic>> users;
  final List<Map<String, dynamic>> tips;
  final List<Map<String, dynamic>> featured;
  final List<Map<String, dynamic>> faq;
}
